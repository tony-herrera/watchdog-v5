import time
import yfinance as yf
from datetime import datetime
from typing import Any, Optional
from core.contracts.common import DataPoint, DeltaPoint
from core.contracts.domain import ValuationInput

class AdapterMetadata:
    def __init__(self, provider: str):
        self.provider = provider
        self.retrieved_at: Optional[datetime] = None
        self.api_version: str = "v1"
        self.latency_ms: int = 0

class YahooDataAdapter:
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.source_tag = "Yahoo Finance"
        self.info = {}
        self.metadata = AdapterMetadata(provider=self.source_tag)

    def fetch(self) -> bool:
        """Explicit network I/O. Safe to wrap in retry logic."""
        start_time = time.time()
        try:
            stock = yf.Ticker(self.ticker)
            self.info = stock.info
            
            self.metadata.retrieved_at = datetime.utcnow()
            self.metadata.latency_ms = int((time.time() - start_time) * 1000)
            return True
        except Exception as e:
            print(f"[{self.source_tag}] Fetch failed for {self.ticker}: {e}")
            return False

    def _make_dp(self, key: str, default: Any = None, confidence: float = 0.9) -> DataPoint:
        val = self.info.get(key, default)
        return DataPoint(value=val, source=self.source_tag, confidence=confidence)

    def build_valuation_input(self) -> Optional[ValuationInput]:
        if not self.info:
            return None # Must call fetch() first

        # Safe DeltaPoint: No fabricated history. 
        # Downstream Validation Engine will see confidence=0.0 and handle it.
        fw_pe_curr = self._make_dp("forwardPE")
        fw_pe_hist = DataPoint(value=None, source="Unavailable", confidence=0.0)
        fw_pe = DeltaPoint(current=fw_pe_curr, historical_90d=fw_pe_hist)
        
        # Calculate Implied Yield safely
        yield_val = None
        if isinstance(fw_pe_curr.value, (int, float)) and fw_pe_curr.value > 0:
            yield_val = 1 / fw_pe_curr.value

        return ValuationInput(
            ticker=self.ticker,
            forward_pe=fw_pe,
            ev_to_ebitda=DeltaPoint(
                current=self._make_dp("enterpriseToEbitda"), 
                historical_90d=DataPoint(value=None, source="Unavailable", confidence=0.0)
            ),
            revenue_growth_next_year=self._make_dp("revenueGrowth", confidence=0.7),
            eps_growth_next_year=self._make_dp("earningsGrowth", confidence=0.7),
            implied_earnings_yield=DataPoint(value=yield_val, source="Calculated", confidence=1.0),
            price_to_book=self._make_dp("priceToBook")
        )