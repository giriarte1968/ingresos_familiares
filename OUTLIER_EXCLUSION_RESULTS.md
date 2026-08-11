# Outlier Exclusion Simulation Results - Alquiler Data Rosario

**Date:** 2026-07-30
**Status:** COMPLETE

## Executive Summary

The outlier exclusion simulation was performed on 4,867 alquiler entries from `cache_scraping.json`. The analysis shows that **most data is already reasonable**, with extreme outliers being a small minority. The medians barely changed after exclusion, indicating the contamination is limited.

---

## Configuration

| Parameter | Value |
|-----------|-------|
| MAD Threshold | 3.0 |
| USD Rate | 1,500 ARS/USD |
| Hard Rule: USD valor_m2 > 25 | EXCLUDE |
| Hard Rule: ARS valor_m2 < 1,000 | EXCLUDE |
| Hard Rule: ARS valor_m2 > 20,000 | EXCLUDE |
| Hard Rule: m2 < 15 | EXCLUDE |
| Hard Rule: m2 > 500 | EXCLUDE |

---

## Part 1: Data Distribution

### ARS Entries (1,386 total)
- **Mean:** 15,572 ARS/m2
- **Median:** 10,455 ARS/m2
- **Std Dev:** 63,578 (high due to outliers)
- **Min:** 0
- **Max:** 1,500,000 (clear contamination)

**Distribution:**
- < 5,000: 107 (7.7%)
- 5,000 - 10,000: 453 (32.7%)
- 10,000 - 15,000: 648 (46.7%)
- 15,000 - 20,000: 117 (8.4%)
- > 20,000: 21 (1.5%)

### USD Entries (3,481 total)
- **Mean:** 41.96 USD/m2 (inflated by outliers)
- **Median:** 9.21 USD/m2
- **Std Dev:** 505.21 (extremely high)
- **Min:** 2.01
- **Max:** 15,833.33 (clearly mislabeled sale data)

**Distribution:**
- < 5: 199 (5.7%)
- 5 - 10: 1,950 (56.0%)
- 10 - 15: 1,113 (32.0%)
- 15 - 20: 130 (3.7%)
- 20 - 25: 29 (0.8%)
- > 25: 26 (0.7%)

---

## Part 2: Zone-by-Zone Exclusion Analysis

| Zone | ARS Orig | ARS Final | ARS Median | Change | USD Orig | USD Final | USD Median | Change |
|------|----------|-----------|------------|--------|----------|-----------|------------|--------|
| Centro | 4 | 3 | $16,000 | +11.6% | 0 | 0 | $0.00 | 0.0% |
| Martin | 18 | 18 | $10,000 | 0.0% | 0 | 0 | $0.00 | 0.0% |
| Otro | 1,284 | 1,172 | $10,431 | +1.4% | 0 | 0 | $0.00 | 0.0% |
| Pellegrini | 27 | 26 | $11,125 | -1.1% | 0 | 0 | $0.00 | 0.0% |
| Puerto Norte | 51 | 39 | $14,912 | +3.2% | 103 | 94 | $12.98 | -3.7% |
| Rosario | 2 | 1 | $18,993 | +99.8% | 3,378 | 3,239 | $9.01 | -1.7% |

### Key Findings:
1. **"Otro" zone** has 1,284 ARS entries (most data) - only +1.4% change
2. **"Rosario" zone** has 3,378 USD entries (most USD data) - only -1.7% change
3. Extreme outliers (up to 1,500,000 ARS/m2 and 15,833 USD/m2) are being removed

---

## Part 3: Overall Median Changes

| Currency | Contaminated | Clean | Change |
|----------|--------------|-------|--------|
| ARS | 10,455 | 10,591 | +1.3% |
| USD | 9.21 | 9.07 | -1.5% |

**Interpretation:** The medians barely changed because:
- Most data is already in the reasonable range (5,000-15,000 ARS/m2)
- Extreme outliers are few (1.5% of ARS, 0.7% of USD)
- Removing high outliers slightly increases ARS median
- Removing high outliers slightly decreases USD median

---

## Part 4: Property Alquiler Simulation

### Property Details

| Property | Lat | Lon | Dorm | m2 |
|----------|-----|-----|------|----|
| Ayacucho 1234 | -32.9333 | -60.6407 | 3 | 85 |
| Mabel | -32.9175 | -60.6825 | 2 | 60 |
| Vera Mujica | -32.9500 | -60.6600 | 2 | 70 |

### Alquiler Calculations

#### Ayacucho 1234 (85 m2, 3 dorm)
| Metric | Contaminated | Clean | Change |
|--------|--------------|-------|--------|
| Alquiler Base | $888,656 | $900,235 | +1.3% |
| Alquiler Final (with CT) | $1,013,770 | $1,026,979 | +1.3% |
| Alquiler USD | $675.85 | $684.65 | +1.3% |
| Cap Rate | 7.34% | 7.44% | +0.10% |

#### Mabel (60 m2, 2 dorm)
| Metric | Contaminated | Clean | Change |
|--------|--------------|-------|--------|
| Alquiler Base | $627,287 | $635,460 | +1.3% |
| Alquiler Final (with CT) | $715,602 | $724,926 | +1.3% |
| Alquiler USD | $477.07 | $483.28 | +1.3% |
| Cap Rate | 7.34% | 7.44% | +0.10% |

#### Vera Mujica (70 m2, 2 dorm)
| Metric | Contaminated | Clean | Change |
|--------|--------------|-------|--------|
| Alquiler Base | $731,835 | $741,370 | +1.3% |
| Alquiler Final (with CT) | $834,869 | $845,747 | +1.3% |
| Alquiler USD | $556.58 | $563.83 | +1.3% |
| Cap Rate | 7.34% | 7.44% | +0.10% |

---

## Part 5: Summary Table

| Property | m2 | Dorm | Current ARS | Clean ARS | Reduction | Current Cap | Clean Cap | Realistic |
|----------|----|----|-------------|-----------|-----------|-------------|-----------|-----------|
| Ayacucho 1234 | 85 | 3 | $1,013,770 | $1,026,979 | -1.3% | 7.34% | 7.44% | NO |
| Mabel | 60 | 2 | $715,602 | $724,926 | -1.3% | 7.34% | 7.44% | NO |
| Vera Mujica | 70 | 2 | $834,869 | $845,747 | -1.3% | 7.34% | 7.44% | NO |

---

## Part 6: Market Context

### Rosario Alquiler Realistic Ranges
- **Alquiler USD:** $4-8/m2/mes
- **Alquiler ARS:** $6,000-12,000/m2/mes (base, before CT)
- **Cap Rate:** 4-6% annual

### Current State
- **Contaminated ARS median:** 10,455 ARS/m2/mes
- **Clean ARS median:** 10,591 ARS/m2/mes
- **Alquiler for 85m2 apt:** ~$900,235 ARS/mes (~$600 USD/mes)

### Analysis

The cap rates (7.3-7.4%) are **higher than realistic** (target: 4-6%). This suggests:

1. **The issue is NOT outlier contamination** - removing outliers barely changed the medians
2. **The issue is likely in the CT (inflation adjustment)** - the +30.14% annual rate may be too aggressive
3. **Or the alquiler data itself is inflated** - perhaps from a different time period or market segment

---

## Conclusions

### 1. Outlier Exclusion Effectiveness
- **Hard rules** removed 108 ARS entries (7.8%) and 148 USD entries (4.3%)
- **MAD-based** removed additional 13 ARS and 136 USD entries
- **Total exclusion:** 121 ARS (8.7%) and 284 USD (8.2%)

### 2. Median Impact
- ARS median: +1.3% (10,455 -> 10,591)
- USD median: -1.5% (9.21 -> 9.07)
- **Minimal impact** - most data was already reasonable

### 3. Property Alquiler Impact
- All properties show +1.3% increase in alquiler after cleaning
- Cap rates remain at 7.3-7.4% (still above realistic 4-6%)

### 4. Root Cause Analysis
The contamination is **NOT the primary cause** of inflated alquiler values. The real issue is likely:
- CT (inflation adjustment) rate of +30.14% annual may be too high
- Base alquiler data may be from a higher market segment
- Or the data needs to be filtered by date (more recent data)

---

## Recommendations

1. **Implement outlier exclusion** - it's working correctly and removing extreme values
2. **Review CT alquiler rate** - consider reducing from 30.14% to match actual inflation
3. **Filter by date** - only use alquiler data from last 6-12 months
4. **Segment by property type** - separate data for apartments vs houses
5. **Validate with real market data** - compare with current rental listings

---

## Technical Details

### Exclusion Rules Applied

**Tier 1 (Hard Rules):**
- USD valor_m2 > 25 -> VENTA_MISLABELED
- ARS valor_m2 < 1,000 -> SUSPICIOUS_LOW
- ARS valor_m2 > 20,000 -> SUSPICIOUS_HIGH
- precio < 500 ARS -> INCOMPLETE_DATA
- m2 < 15 -> SMALL_AREA
- m2 > 500 -> LARGE_AREA

**Tier 2 (MAD-based):**
- Modified Z-Score = 0.6745 * (x - median) / MAD
- Exclude if |Modified Z| > 3.0

### Files Generated
- `simulation_outlier_exclusion.py` - Basic exclusion simulation
- `simulation_detailed_analysis.py` - Detailed data distribution analysis
- `simulation_zone_analysis.py` - Zone-by-zone analysis
- `simulation_complete.py` - Complete simulation with property calculations
