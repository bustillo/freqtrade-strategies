# 🚀 Freqtrade Trading Strategies Repository  
A collection of automated trading strategies for Freqtrade, designed for cryptocurrency markets.  
Includes configurations, custom logic, and documentation for seamless implementation.  

---

## 📈 Available Strategies  

### 1. **ZaratustraDCA2_06** ([Code](ZaratustraDCA/ZaratustraDCA2_06.py) | [Config](ZaratustraDCA/config.ZaratustraDCA2_06.json))  
- **Description**: Advanced futures trading strategy combining **Dollar Cost Averaging (DCA)** with dynamic risk management, trend-following signals, and partial profit-taking logic.  
- **Features**:  
  - **Multi-directional Trading**: Supports both Long and Short positions in futures markets.  
  - **Dynamic Position Sizing**:  
    - **50% fixed stake increase per additional entry**: Each DCA re-entry increases the position size by 50% of the initial stake to average down/up.
  - **Entry Signals**:  
    - **Longs**: DX > PDI & ADX > MDI & PDI > MDI.  
    - **Shorts**: DX > MDI & ADX > PDI & MDI > PDI.  
  - **Exit Signals**:  
    - **Longs**: DX crosses below ADX & ADX > 25.  
    - **Shorts**: PDI crosses above MDI & ADX < 25.
  - **Risk Protections**:  
    - Fixed stop-loss (-10%).  
    - Cooldown mechanisms to prevent overtrading.  
    - StoplossGuard to pause trading after consecutive losses.  
  - **Technical Backbone**:  
    - Uses ADX, PDI/MDI for trend analysis.  
    - Volume-weighted indicators to filter noise.  

- **Execution**:  
  ```bash  
  freqtrade trade --strategy ZaratustraDCA2_06 --config config.ZaratustraDCA2_06.json  

### 2. **ZaratustraDCA2_07** ([Code](ZaratustraDCA/ZaratustraDCA2_07.py) | [Config](ZaratustraDCA/config.ZaratustraDCA2_07.json))  
- **Description**: Enhanced futures strategy combining adaptive **Dollar Cost Averaging (DCA)** with volatility-adjusted trend signals, dynamic exits, and hyper-optimizable risk parameters.  
- **Features**:  
  - **Multi-directional Trading**: Supports Long/Short positions with context-aware entries. 
  - **Adaptive Position Sizing**:  
    - **Dynamic DCA**:  Adds positions only when ADX thresholds (adjusted by ATR volatility) confirm trend strength.
    - **Auto-partial Exits**:  Closes 50% of position at +10% unrealized profit.
  - **Entry Signals**:  
    - **Longs/Shorts**: ADX > dynamic threshold (20 + (ATR% × adx_high_multiplier)) + directional alignment (PDI > MDI / MDI > PDI).    
  - **Exit Signals**:  
    - **Profit-Taking**: Partial close at +10% profit (first exit).  
    - **Trend Weakness Exit**: Closes 30% position if ADX < dynamic threshold (max(20 - (ATR% × adx_low_multiplier), 5)).
  - **Risk Protections**:  
    - **Drawdown Limits**: Blocks new entries if current profit < -4% (1st entry), -6% (2nd), -8% (3rd+). 
    - Fixed stop-loss (-10%) + StoplossGuard + Cooldown mechanisms.  
  - **Technical Backbone**:  
    - ADX/PDI/MDI for trend direction + ATR volatility scaling. 
  - **Hyperopt Parameters**:  
  ```python  
  adx_high_multiplier = DecimalParameter(0.3, 0.7, default=0.5, optimize=True)  # Aggressiveness in strong trends 
  adx_low_multiplier = DecimalParameter(0.1, 0.5, default=0.3, optimize=True)   # Sensitivity to trend weakness

- **Execution**:  
  ```bash  
  freqtrade trade --strategy ZaratustraDCA2_07 --config config.ZaratustraDCA2_07.json  

### Key Differences from v2_06:

| Aspect               | v2_06                          | v2_07                                   |
|----------------------|--------------------------------|-----------------------------------------|
| **DCA Triggers**     | Fixed ADX thresholds           | ATR-scaled dynamic ADX thresholds       |
| **Profit Taking**    | Manual/Trailing SL             | Automatic 50% partial exit at +10%      |
| **Risk Adaptation**  | Static rules                   | Volatility-adjusted position management |
| **Optimization**     | Fixed parameters               | Tunable ADX/ATR multipliers via Hyperopt|

---

## ⚙️ Installation & Setup  

1. **Requirements**:  
   - Python 3.8+  
   - [Freqtrade](https://www.freqtrade.io/) installed.  
   ```bash  
   git clone https://github.com/bustillo/freqtrade-strategies.git  
   cd freqtrade-strategies  
