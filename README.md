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

### 2. **Other Strategies** (Coming Soon)  
- *Melquiades*: 5m timeframe strategy (Coming Soon).   

---

## ⚙️ Installation & Setup  

1. **Requirements**:  
   - Python 3.8+  
   - [Freqtrade](https://www.freqtrade.io/) installed.  
   ```bash  
   git clone https://github.com/bustillo/freqtrade-strategies.git  
   cd freqtrade-strategies  
