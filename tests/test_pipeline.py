import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.config.settings import SEARCH_CHANNELS, get_api_credentials
from src.api.mock_data import generate_mock_search_data, generate_mock_trend_data
from src.analysis.eda_engine import compute_channel_totals_df, compute_kpi_metrics
from src.analysis.text_mining import extract_top_words

print("1. Testing config...")
creds = get_api_credentials()
print(f"   Credentials configured: {creds['is_configured']}, API HUB: {creds['is_hub']}")
assert len(SEARCH_CHANNELS) == 8
print("   8 Search channels verified.")

print("2. Testing mock data generation...")
keywords = ["아이폰", "갤럭시"]
channel_ids = list(SEARCH_CHANNELS.keys())
df_items, totals = generate_mock_search_data(keywords, channel_ids, display_per_channel=10)
print(f"   Generated {len(df_items)} items across {len(totals)} keywords.")
assert not df_items.empty

df_trend = generate_mock_trend_data(keywords, "2026-06-01", "2026-09-01", "date")
print(f"   Generated {len(df_trend)} trend data points.")
assert not df_trend.empty

print("3. Testing EDA engine...")
df_channels = compute_channel_totals_df(totals)
assert not df_channels.empty
kpi = compute_kpi_metrics(df_items, totals, df_trend)
print(f"   KPI Summary: Grand Total={kpi['grand_total']}, Top KW={kpi['top_keyword']}, Leader={kpi['trend_leader']}")
assert kpi["estimated_total"] == kpi["grand_total"]
assert kpi["collected_items_count"] == len(df_items)

print("4. Testing text mining...")
words_df = extract_top_words(df_items, top_n=10)
print(f"   Extracted top words:\n{words_df.head(5)}")

print("\nAll pipeline components tested successfully!")
