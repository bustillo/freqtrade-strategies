import logging
import numpy as np
import pandas as pd
from technical import qtpylib
from pandas import DataFrame
from datetime import datetime, timezone
from typing import Optional
from functools import reduce
import talib.abstract as ta
import pandas_ta as pta
from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter, RealParameter, merge_informative_pair)
import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.persistence import Trade

logger = logging.getLogger(__name__)


class ZaratustraDCA2_07(IStrategy):
    """
        Personalized Trading Strategy with Risk Management, DCA, and Technical Indicators

        This automated strategy combines advanced risk management techniques with Dollar Cost Averaging (DCA)
        to optimize market operations. The strategy employs technical indicators (e.g., ADX, PDI, MDI) to define entry
        and exit conditions for both long and short positions. It also includes dynamic stoploss logic based on ATR and
        protections like cooldown periods and loss guards.

        Key features:
        - Long and short trading enabled with dynamic position adjustments.
        - Protections against overtrading using cooldown mechanisms.
        - Use of technical indicators to track market trends and trigger signals.
        - Supports dynamic stake adjustments based on successful trade entries.

        NOTE: This strategy is under development, and some functions may be disabled or incomplete. Parameters like ROI
        targets and advanced stoploss logic are subject to future optimization. Test thoroughly before using it in live trading.

        Telegram Profile: https://t.me/bustillo

        Choose your coffee style:  
        - BTC (Classic): bc1qfq46qqhurg8ps73506rtqsr26mfhl9t6vp2ltc
        - ETH/ERC-20 & BSC/BEP-20 (Smart): 0x486Ef431878e2a240ea2e7A6EBA42e74632c265c
          (Supports ETH, BNB, USDT, and tokens on: Ethereum, Binance Smart Chain, and EVM-compatible networks.)
        - SOL (Speed): 2nrYABUJLjHtUdVTXkcY8ELUK7q3HH4iWXQxQMQDdZa8
        - XMR (Privacy): 45kQh8n23AgiY2yEDbMmJdcMGTaHmpn6vFfhECs7EwtPZ7pbyCQAyzDCehtDZSGsWzaDGir1LfA4EGDQP3dtPStsMdrzUG5
    """

    ### Strategy parameters ###

    exit_profit_only = True
    use_custom_stoploss = False
    trailing_stop = False
    ignore_roi_if_entry_signal = True
    can_short = True
    use_exit_signal = True
    stoploss = -0.10
    startup_candle_count: int = 100
    timeframe = '5m'

    # DCA Parameters
    position_adjustment_enable = True
    max_entry_position_adjustment = 2
    max_dca_multiplier = 1  # Maximum DCA multiplier

    # ROI table:
    minimal_roi = {}

    ### Hyperopt ###

    # protections
    cooldown_lookback = IntParameter(2, 48, default=5, space="protection", optimize=True)
    stop_duration = IntParameter(12, 120, default=72, space="protection", optimize=True)
    use_stop_protection = BooleanParameter(default=True, space="protection", optimize=True)

    # ADX Threshold Multipliers (Used in adjust_trade_position logic)
    # ------------------------------------------------
    # adx_high_multiplier: Scales ATR% contribution to upper ADX threshold (DCA entries)
    # - Range: 0.3-0.7 | Higher = more aggressive entries in volatile trends
    adx_high_multiplier = DecimalParameter(0.3, 0.7, default=0.5, space='buy', optimize=True)

    # adx_low_multiplier: Scales ATR% deduction for lower ADX threshold (partial exits)
    # - Range: 0.1-0.5 | Higher = earlier exits in low-volatility environments  
    adx_low_multiplier = DecimalParameter(0.1, 0.5, default=0.3, space='buy', optimize=True)


    ### Protections ###
    @property
    def protections(self):
        """
            Defines the protections to apply during trading operations.
        """

        prot = []

        prot.append({
            "method": "CooldownPeriod",
            "stop_duration_candles": self.cooldown_lookback.value
        })
        if self.use_stop_protection.value:
            prot.append({
                "method": "StoplossGuard",
                "lookback_period_candles": 24 * 3,
                "trade_limit": 1,
                "stop_duration_candles": self.stop_duration.value,
                "only_per_pair": False
            })

        return prot

    ### Dollar Cost Averaging (DCA) ###
    # This is called when placing the initial order (opening trade)
    def custom_stake_amount(self, pair: str, current_time: datetime, current_rate: float,
                            proposed_stake: float, min_stake: Optional[float], max_stake: float,
                            leverage: float, entry_tag: Optional[str], side: str,
                            **kwargs) -> float:
        """
            Calculates the stake amount to use for a trade, adjusted dynamically based on the DCA multiplier.
            - The proposed stake is divided by the maximum DCA multiplier (`self.max_dca_multiplier`)
              to determine the adjusted stake.
            - If the adjusted stake is lower than the allowed minimum (`min_stake`), it is automatically increased
              to meet the minimum stake requirement.
        """

        # Calculates the adjusted stake amount based on the DCA multiplier.
        adjusted_stake = proposed_stake / self.max_dca_multiplier

        # Automatically adjusts to the minimum stake if it is too low.
        if adjusted_stake < min_stake:
            adjusted_stake = min_stake

        return adjusted_stake

    def adjust_trade_position(self, trade: Trade, current_time: datetime,
                              current_rate: float, current_profit: float,
                              min_stake: Optional[float], max_stake: float,
                              current_entry_rate: float, current_exit_rate: float,
                              current_entry_profit: float, current_exit_profit: float,
                              **kwargs) -> Optional[float]:
        """
            Dynamic position management system combining adaptive DCA entries, volatility-based exits, and profit-taking rules.  
            Only executed when `position_adjustment_enable = True`.  
            Key Features:  
              Smart DCA Blocking:  
               - Blocks new entries if drawdown exceeds:  
                 - -4% (1st entry), -6% (2nd), -8% (3rd+)  
              Auto Profit-Taking:  
               - Closes 50% position at +10% unrealized profit (first exit).  
              Volatility-Adjusted Entries:  
               - Adds positions only when:  
                 - ADX > threshold_high (20 + (ATR% × adx_high_multiplier))  
                 - Trend direction aligned (PDI > MDI for longs, MDI > PDI for shorts)  
               - Stake size grows 50% per DCA level.  
              Early Trend Weakness Detection:  
               - Closes 30% position if ADX < threshold_low (max(20 - (ATR% × adx_low_multiplier), 5).  
              Hard Limits:  
               - Max 3 DCA entries per trade.  
               - Always respects min/max stake constraints.  
        """

        dataframe, _ = self.dp.get_analyzed_dataframe(trade.pair, self.timeframe)
        if dataframe.empty:
            return None

        if trade.nr_of_successful_entries > 0:
            if trade.entry_side == "buy":
                if (trade.nr_of_successful_entries == 1 and current_profit > -0.04) or \
                   (trade.nr_of_successful_entries == 2 and current_profit > -0.06) or \
                   (trade.nr_of_successful_entries >= 3 and current_profit > -0.08):
                    return None
            else:
                if (trade.nr_of_successful_entries == 1 and current_profit > -0.04) or \
                   (trade.nr_of_successful_entries == 2 and current_profit > -0.06) or \
                   (trade.nr_of_successful_entries >= 3 and current_profit > -0.08):
                    return None

        if current_profit > 0.10 and trade.nr_of_successful_exits == 0:
            return -(trade.stake_amount / 2)

        max_dca_entries = 3
        if trade.nr_of_successful_entries >= max_dca_entries:
            return None

        atr = dataframe['atr'].iloc[-1]
        adx = dataframe['adx'].iloc[-1]
        pdi = dataframe['pdi'].iloc[-1]
        mdi = dataframe['mdi'].iloc[-1]

        atr_percent = (atr / current_rate) * 100
        adx_threshold_high = 20 + (atr_percent * self.adx_high_multiplier.value)
        adx_threshold_low = max(20 - (atr_percent * self.adx_low_multiplier.value), 5)

        if adx > adx_threshold_high:
            if (trade.entry_side == "buy" and pdi > mdi) or (trade.entry_side == "sell" and mdi > pdi):
                filled_entries = trade.select_filled_orders(trade.entry_side)
                if not filled_entries:
                    return None
                stake_amount = filled_entries[0].cost * (1 + 0.5 * (trade.nr_of_successful_entries - 1))
                return min(stake_amount, max_stake)

        elif adx < adx_threshold_low:
            return -trade.stake_amount * 0.3

        return None

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
            Calculates technical indicators used to define entry and exit signals.
        """
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        dataframe['dx']  = ta.SMA(ta.DX(dataframe) * dataframe['volume']) / ta.SMA(dataframe['volume'])
        dataframe['adx'] = ta.SMA(ta.ADX(dataframe) * dataframe['volume']) / ta.SMA(dataframe['volume'])
        dataframe['pdi'] = ta.SMA(ta.PLUS_DI(dataframe) * dataframe['volume']) / ta.SMA(dataframe['volume'])
        dataframe['mdi'] = ta.SMA(ta.MINUS_DI(dataframe) * dataframe['volume']) / ta.SMA(dataframe['volume'])

        return dataframe

    def populate_entry_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        """
            Defines the conditions for long/short entries based on
            technical indicators such as ADX, PDI, and MDI.
        """

        df.loc[
            (
                    (qtpylib.crossed_above(df['dx'], df['pdi'])) &
                    (df['adx'] > df['mdi']) &
                    (df['pdi'] > df['mdi'])
            ),
            ['enter_long', 'enter_tag']
        ] = (1, 'Entry Long (DX↑PDI & ADX>MDI & PDI>MDI)')

        df.loc[
            (
                    (qtpylib.crossed_above(df['dx'], df['mdi'])) &
                    (df['adx'] > df['pdi']) &
                    (df['mdi'] > df['pdi'])
            ),
            ['enter_short', 'enter_tag']
        ] = (1, 'Entry Short (DX↑MDI & ADX>PDI & MDI>PDI)')

        return df

    def populate_exit_trend(self, df: DataFrame, metadata: dict) -> DataFrame:
        """
            Defines exit conditions for trades based on the ADX indicator:
            - Exit Long: Triggered when 'dx' crosses below 'adx' and ADX is strong (>25).
            - Exit Short: PDI crosses above MDI (momentum reversal) AND weak trend strength (ADX <25).
        """

        df.loc[
            (
                    (qtpylib.crossed_below(df['dx'], df['adx'])) &
                    (df['adx'] > 25)
            ),
            ['exit_long', 'exit_tag']
        ] = (1, 'Exit Long (DX↓ADX & ADX>25)')

        df.loc[
            (
                    (qtpylib.crossed_above(df['pdi'], df['mdi'])) &
                    (df['adx'] < 25)
            ),
            ['exit_short', 'exit_tag']
        ] = (1, 'Exit Short (PDI↑MDI & ADX<25)')

        return df
