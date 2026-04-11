"""Static profile data for fixed heatmap universes.

Name / sector / marketCap for the SP500 top-20 and NASDAQ-100 universes are
baked in here so the heatmap refresh loop never has to call Finnhub's
`/stock/profile2` endpoint. Market cap numbers are in millions USD and are
used **only for treemap tile sizing** — being off by 20-30% is visually
indistinguishable in the final render, so approximate values from late 2024 /
2025 are good enough and don't need to be kept up to date.

`changePct`/`price`/`prevClose` are fetched live; everything in this file is
the slowly-changing metadata.
"""

from __future__ import annotations

from typing import TypedDict


class UniverseEntry(TypedDict):
    name: str
    sector: str
    marketCap: float  # millions USD, approximate


# S&P 500 top-20 by market cap. Kept small for a "highlights" view.
SP500_TOP: dict[str, UniverseEntry] = {
    "AAPL":  {"name": "Apple Inc.",             "sector": "Technology",          "marketCap": 3_500_000},
    "MSFT":  {"name": "Microsoft Corporation",  "sector": "Technology",          "marketCap": 3_300_000},
    "NVDA":  {"name": "NVIDIA Corporation",     "sector": "Technology",          "marketCap": 3_200_000},
    "GOOGL": {"name": "Alphabet Inc. (Class A)","sector": "Communications",      "marketCap": 2_100_000},
    "AMZN":  {"name": "Amazon.com Inc.",        "sector": "Retail",              "marketCap": 2_000_000},
    "META":  {"name": "Meta Platforms Inc.",    "sector": "Communications",      "marketCap": 1_500_000},
    "BRK.B": {"name": "Berkshire Hathaway",     "sector": "Financial Services",  "marketCap":   950_000},
    "TSLA":  {"name": "Tesla Inc.",             "sector": "Automobiles",         "marketCap":   900_000},
    "AVGO":  {"name": "Broadcom Inc.",          "sector": "Technology",          "marketCap":   850_000},
    "LLY":   {"name": "Eli Lilly and Co.",      "sector": "Pharmaceuticals",     "marketCap":   750_000},
    "JPM":   {"name": "JPMorgan Chase & Co.",   "sector": "Financial Services",  "marketCap":   650_000},
    "V":     {"name": "Visa Inc.",              "sector": "Financial Services",  "marketCap":   580_000},
    "WMT":   {"name": "Walmart Inc.",           "sector": "Retail",              "marketCap":   560_000},
    "XOM":   {"name": "Exxon Mobil Corp.",      "sector": "Energy",              "marketCap":   520_000},
    "UNH":   {"name": "UnitedHealth Group",     "sector": "Health Care",         "marketCap":   500_000},
    "MA":    {"name": "Mastercard Inc.",        "sector": "Financial Services",  "marketCap":   470_000},
    "PG":    {"name": "Procter & Gamble",       "sector": "Consumer Goods",      "marketCap":   410_000},
    "JNJ":   {"name": "Johnson & Johnson",      "sector": "Pharmaceuticals",     "marketCap":   390_000},
    "HD":    {"name": "The Home Depot",         "sector": "Retail",              "marketCap":   380_000},
    "COST":  {"name": "Costco Wholesale",       "sector": "Retail",              "marketCap":   380_000},
}


# NASDAQ-100. Membership drifts over time; this is a stable-ish snapshot.
NASDAQ_100: dict[str, UniverseEntry] = {
    "AAPL":  {"name": "Apple Inc.",                 "sector": "Technology",         "marketCap": 3_500_000},
    "MSFT":  {"name": "Microsoft Corporation",      "sector": "Technology",         "marketCap": 3_300_000},
    "NVDA":  {"name": "NVIDIA Corporation",         "sector": "Technology",         "marketCap": 3_200_000},
    "AMZN":  {"name": "Amazon.com Inc.",            "sector": "Retail",             "marketCap": 2_000_000},
    "GOOGL": {"name": "Alphabet Inc. (Class A)",    "sector": "Communications",     "marketCap": 1_050_000},
    "GOOG":  {"name": "Alphabet Inc. (Class C)",    "sector": "Communications",     "marketCap": 1_050_000},
    "META":  {"name": "Meta Platforms Inc.",        "sector": "Communications",     "marketCap": 1_500_000},
    "TSLA":  {"name": "Tesla Inc.",                 "sector": "Automobiles",        "marketCap":   900_000},
    "AVGO":  {"name": "Broadcom Inc.",              "sector": "Technology",         "marketCap":   850_000},
    "COST":  {"name": "Costco Wholesale",           "sector": "Retail",             "marketCap":   380_000},
    "NFLX":  {"name": "Netflix Inc.",               "sector": "Communications",     "marketCap":   300_000},
    "TMUS":  {"name": "T-Mobile US",                "sector": "Communications",     "marketCap":   250_000},
    "PEP":   {"name": "PepsiCo Inc.",               "sector": "Consumer Goods",     "marketCap":   240_000},
    "ADBE":  {"name": "Adobe Inc.",                 "sector": "Technology",         "marketCap":   230_000},
    "CSCO":  {"name": "Cisco Systems",              "sector": "Technology",         "marketCap":   220_000},
    "AMD":   {"name": "Advanced Micro Devices",     "sector": "Technology",         "marketCap":   210_000},
    "INTC":  {"name": "Intel Corporation",          "sector": "Technology",         "marketCap":   180_000},
    "QCOM":  {"name": "Qualcomm Inc.",              "sector": "Technology",         "marketCap":   190_000},
    "TXN":   {"name": "Texas Instruments",          "sector": "Technology",         "marketCap":   180_000},
    "CMCSA": {"name": "Comcast Corporation",        "sector": "Communications",     "marketCap":   170_000},
    "AMGN":  {"name": "Amgen Inc.",                 "sector": "Pharmaceuticals",    "marketCap":   160_000},
    "INTU":  {"name": "Intuit Inc.",                "sector": "Technology",         "marketCap":   180_000},
    "AMAT":  {"name": "Applied Materials",          "sector": "Technology",         "marketCap":   160_000},
    "HON":   {"name": "Honeywell International",    "sector": "Industrials",        "marketCap":   140_000},
    "ISRG":  {"name": "Intuitive Surgical",         "sector": "Health Care",        "marketCap":   150_000},
    "BKNG":  {"name": "Booking Holdings",           "sector": "Consumer Services",  "marketCap":   140_000},
    "VRTX":  {"name": "Vertex Pharmaceuticals",     "sector": "Pharmaceuticals",    "marketCap":   120_000},
    "LRCX":  {"name": "Lam Research",               "sector": "Technology",         "marketCap":   110_000},
    "ADP":   {"name": "Automatic Data Processing",  "sector": "Technology",         "marketCap":   115_000},
    "MU":    {"name": "Micron Technology",          "sector": "Technology",         "marketCap":   110_000},
    "PANW":  {"name": "Palo Alto Networks",         "sector": "Technology",         "marketCap":   120_000},
    "REGN":  {"name": "Regeneron Pharmaceuticals",  "sector": "Pharmaceuticals",    "marketCap":   100_000},
    "GILD":  {"name": "Gilead Sciences",            "sector": "Pharmaceuticals",    "marketCap":    95_000},
    "KLAC":  {"name": "KLA Corporation",            "sector": "Technology",         "marketCap":   100_000},
    "MDLZ":  {"name": "Mondelez International",     "sector": "Consumer Goods",     "marketCap":    95_000},
    "ADI":   {"name": "Analog Devices",             "sector": "Technology",         "marketCap":   110_000},
    "SBUX":  {"name": "Starbucks Corporation",      "sector": "Consumer Services",  "marketCap":   100_000},
    "SNPS":  {"name": "Synopsys Inc.",              "sector": "Technology",         "marketCap":    85_000},
    "CDNS":  {"name": "Cadence Design Systems",     "sector": "Technology",         "marketCap":    80_000},
    "ASML":  {"name": "ASML Holding",               "sector": "Technology",         "marketCap":   320_000},
    "MELI":  {"name": "MercadoLibre",               "sector": "Retail",             "marketCap":    95_000},
    "CRWD":  {"name": "CrowdStrike Holdings",       "sector": "Technology",         "marketCap":    85_000},
    "ABNB":  {"name": "Airbnb Inc.",                "sector": "Consumer Services",  "marketCap":    90_000},
    "MAR":   {"name": "Marriott International",     "sector": "Consumer Services",  "marketCap":    70_000},
    "PYPL":  {"name": "PayPal Holdings",            "sector": "Financial Services", "marketCap":    75_000},
    "FTNT":  {"name": "Fortinet Inc.",              "sector": "Technology",         "marketCap":    75_000},
    "ORLY":  {"name": "O'Reilly Automotive",        "sector": "Retail",             "marketCap":    65_000},
    "ADSK":  {"name": "Autodesk Inc.",              "sector": "Technology",         "marketCap":    60_000},
    "CTAS":  {"name": "Cintas Corporation",         "sector": "Industrials",        "marketCap":    80_000},
    "CSX":   {"name": "CSX Corporation",            "sector": "Industrials",        "marketCap":    65_000},
    "MNST":  {"name": "Monster Beverage",           "sector": "Consumer Goods",     "marketCap":    60_000},
    "PCAR":  {"name": "PACCAR Inc.",                "sector": "Industrials",        "marketCap":    55_000},
    "PAYX":  {"name": "Paychex Inc.",               "sector": "Technology",         "marketCap":    50_000},
    "ROP":   {"name": "Roper Technologies",         "sector": "Industrials",        "marketCap":    60_000},
    "NXPI":  {"name": "NXP Semiconductors",         "sector": "Technology",         "marketCap":    60_000},
    "WDAY":  {"name": "Workday Inc.",               "sector": "Technology",         "marketCap":    65_000},
    "AEP":   {"name": "American Electric Power",    "sector": "Utilities",          "marketCap":    50_000},
    "ROST":  {"name": "Ross Stores",                "sector": "Retail",             "marketCap":    50_000},
    "MRVL":  {"name": "Marvell Technology",         "sector": "Technology",         "marketCap":    70_000},
    "FAST":  {"name": "Fastenal Company",           "sector": "Industrials",        "marketCap":    45_000},
    "CPRT":  {"name": "Copart Inc.",                "sector": "Industrials",        "marketCap":    50_000},
    "DXCM":  {"name": "DexCom Inc.",                "sector": "Health Care",        "marketCap":    40_000},
    "KDP":   {"name": "Keurig Dr Pepper",           "sector": "Consumer Goods",     "marketCap":    48_000},
    "XEL":   {"name": "Xcel Energy",                "sector": "Utilities",          "marketCap":    35_000},
    "IDXX":  {"name": "IDEXX Laboratories",         "sector": "Health Care",        "marketCap":    40_000},
    "ODFL":  {"name": "Old Dominion Freight Line",  "sector": "Industrials",        "marketCap":    42_000},
    "EXC":   {"name": "Exelon Corporation",         "sector": "Utilities",          "marketCap":    38_000},
    "EA":    {"name": "Electronic Arts",            "sector": "Communications",     "marketCap":    40_000},
    "TEAM":  {"name": "Atlassian Corporation",      "sector": "Technology",         "marketCap":    50_000},
    "DDOG":  {"name": "Datadog Inc.",               "sector": "Technology",         "marketCap":    45_000},
    "VRSK":  {"name": "Verisk Analytics",           "sector": "Industrials",        "marketCap":    40_000},
    "CTSH":  {"name": "Cognizant Technology",       "sector": "Technology",         "marketCap":    38_000},
    "LULU":  {"name": "Lululemon Athletica",        "sector": "Retail",             "marketCap":    40_000},
    "KHC":   {"name": "Kraft Heinz Company",        "sector": "Consumer Goods",     "marketCap":    42_000},
    "GEHC":  {"name": "GE HealthCare",              "sector": "Health Care",        "marketCap":    38_000},
    "AZN":   {"name": "AstraZeneca",                "sector": "Pharmaceuticals",    "marketCap":   220_000},
    "FANG":  {"name": "Diamondback Energy",         "sector": "Energy",             "marketCap":    35_000},
    "BKR":   {"name": "Baker Hughes",               "sector": "Energy",             "marketCap":    36_000},
    "ZS":    {"name": "Zscaler Inc.",               "sector": "Technology",         "marketCap":    30_000},
    "ANSS":  {"name": "ANSYS Inc.",                 "sector": "Technology",         "marketCap":    30_000},
    "ON":    {"name": "ON Semiconductor",           "sector": "Technology",         "marketCap":    32_000},
    "TTWO":  {"name": "Take-Two Interactive",       "sector": "Communications",     "marketCap":    28_000},
    "CDW":   {"name": "CDW Corporation",            "sector": "Technology",         "marketCap":    28_000},
    "GFS":   {"name": "GlobalFoundries",            "sector": "Technology",         "marketCap":    28_000},
    "MDB":   {"name": "MongoDB Inc.",               "sector": "Technology",         "marketCap":    25_000},
    "ILMN":  {"name": "Illumina Inc.",              "sector": "Health Care",        "marketCap":    22_000},
    "CEG":   {"name": "Constellation Energy",       "sector": "Utilities",          "marketCap":    70_000},
    "CCEP":  {"name": "Coca-Cola Europacific",      "sector": "Consumer Goods",     "marketCap":    35_000},
    "BIIB":  {"name": "Biogen Inc.",                "sector": "Pharmaceuticals",    "marketCap":    25_000},
    "DLTR":  {"name": "Dollar Tree Inc.",           "sector": "Retail",             "marketCap":    22_000},
    "WBD":   {"name": "Warner Bros. Discovery",     "sector": "Communications",     "marketCap":    20_000},
    "MRNA":  {"name": "Moderna Inc.",               "sector": "Pharmaceuticals",    "marketCap":    18_000},
    "SIRI":  {"name": "Sirius XM Holdings",         "sector": "Communications",     "marketCap":    15_000},
    "WBA":   {"name": "Walgreens Boots Alliance",   "sector": "Retail",             "marketCap":    14_000},
    "MCHP":  {"name": "Microchip Technology",       "sector": "Technology",         "marketCap":    40_000},
    "ROST":  {"name": "Ross Stores",                "sector": "Retail",             "marketCap":    50_000},
    "PDD":   {"name": "PDD Holdings",               "sector": "Retail",             "marketCap":   160_000},
    "LIN":   {"name": "Linde plc",                  "sector": "Basic Materials",    "marketCap":   220_000},
    "TTD":   {"name": "The Trade Desk",             "sector": "Technology",         "marketCap":    55_000},
    "DASH":  {"name": "DoorDash Inc.",              "sector": "Consumer Services",  "marketCap":    55_000},
}


UNIVERSES: dict[str, dict[str, UniverseEntry]] = {
    "sp500": SP500_TOP,
    "nasdaq": NASDAQ_100,
}


def get_universe_symbols(universe: str) -> list[str]:
    """Return the symbol list for a fixed universe, or empty if unknown."""
    return list(UNIVERSES.get(universe, {}).keys())


def get_universe_entry(universe: str, symbol: str) -> UniverseEntry | None:
    return UNIVERSES.get(universe, {}).get(symbol)
