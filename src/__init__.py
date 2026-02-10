# EmotionQuant - 情绪驱动量化交易系统
from importlib.metadata import PackageNotFoundError, version

"""
EmotionQuant: Emotion-driven quantitative trading system for China A-shares market.

Core modules:
- config: Configuration management
- data: Data layer (repositories, models)
- algorithms: Core algorithms (MSS, IRS, PAS)
- integration: Three-thirds integration
- trading: Trading and risk management
- backtest: Backtesting engine
- gui: Streamlit dashboard
- analysis: Performance analysis and reports
"""

try:
    __version__ = version("emotionquant")
except PackageNotFoundError:  # pragma: no cover
    # Keep fallback non-semantic to avoid introducing a second version source.
    __version__ = "unknown"
__author__ = "EmotionQuant Project"
