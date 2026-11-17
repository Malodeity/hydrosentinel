# Province-level non-revenue water (NRW) from the DWS "Analysis of water losses and non-revenue water in South Africa" report
# (data/raw/benchmarking_2022.pdf, Figure 14, 2020/21 water balances). The No Drop PDF has no NRW per authority, so authorities with no NRW of
# their own show their province's average, marked as an estimate. This is display only: it is never stored and the risk model never sees it.

PROVINCE_NRW_PERCENT: dict[str, float] = {
    "Eastern Cape": 46.5,
    "Free State": 52.9,
    "Gauteng": 42.1,
    "KwaZulu-Natal": 48.3,
    "Limpopo": 57.3,
    "Mpumalanga": 50.7,
    "Northern Cape": 55.4,
    "North West": 50.6,
    "Western Cape": 24.8,
}
NRW_ESTIMATE_NOTE = "Province average, DWS water-loss report (2020/21). Not this authority's own figure."
