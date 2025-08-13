# Multi-Method Search Implementation Guide

## 🚀 Overview

This implementation provides 5 different search methods with field-specific indexing:

- **Dense Search**: Semantic search on descriptions only
- **BM25 Search**: Keyword search on descriptions + part numbers
- **MiniCOIL Search**: Neural keyword search on descriptions + part numbers
- **Hybrid BM25**: Dense + BM25 fusion search
- **Hybrid MiniCOIL**: Dense + MiniCOIL fusion search

## 🔧 Setup Instructions

### 1. Index Data with Multiple Vector Types

```bash
cd scripts
python indexing.py --products-file ../data/import/full/products.json
```

This will create a single collection with:
- **Dense vectors**: From shortDescription_airgas_text only
- **BM25 sparse vectors**: From shortDescription + partNumber + manufacturerPartNumber
- **MiniCOIL sparse vectors**: From shortDescription + partNumber + manufacturerPartNumber

### 2. Start the API Service

```bash
cd ..
python -m app.main
```

### 3. Start the Streamlit UI

```bash
cd search_ui
streamlit run search.py
```

## 🔗 API Endpoints

### Individual Search Methods

#### Dense Search (Descriptions Only)
```
GET /api/search/dense?query=gas torch&limit=10
```
- **Fields**: shortDescription_airgas_text
- **Type**: Semantic vector search

#### BM25 Search (Descriptions + Part Numbers)  
```
GET /api/search/bm25?query=HYP220479&limit=10
```
- **Fields**: shortDescription + partNumber + manufacturerPartNumber
- **Type**: Traditional keyword search

#### MiniCOIL Search (Descriptions + Part Numbers)
```
GET /api/search/minicoil?query=welding torch&limit=10
```
- **Fields**: shortDescription + partNumber + manufacturerPartNumber  
- **Type**: Neural sparse search

#### Hybrid BM25 Search
```
GET /api/search/hybrid-bm25?query=safety equipment&limit=10&fusion_alpha=0.6
```
- **Type**: Dense + BM25 fusion
- **fusion_alpha**: 0.0=sparse only, 1.0=dense only

#### Hybrid MiniCOIL Search
```
GET /api/search/hybrid-minicoil?query=regulator valve&limit=10&fusion_alpha=0.4
```
- **Type**: Dense + MiniCOIL fusion
- **fusion_alpha**: 0.0=sparse only, 1.0=dense only

### Utility Endpoints

#### Test Service
```
GET /api/search/test
```

#### Methods Information
```
GET /api/search/methods-info
```

## 🎯 Search Strategy Guide

### When to Use Each Method

| Query Type | Recommended Method | Reason |
|------------|-------------------|---------|
| Product descriptions | **Dense** | Semantic understanding of descriptions |
| Exact part numbers | **BM25** or **MiniCOIL** | Exact matching on part number fields |
| Mixed queries | **Hybrid** methods | Combines semantic + exact matching |
| Broad product categories | **Dense** | Better semantic understanding |
| Technical specifications | **MiniCOIL** | Neural understanding of technical terms |

### Example Queries

**Dense Search (Descriptions Only):**
- "gas welding torch" ✅ Semantic match on descriptions
- "safety equipment" ✅ Broad category understanding  
- "HYP220479" ❌ Part numbers not in description field

**Sparse Search (Descriptions + Part Numbers):**
- "HYP220479" ✅ Exact part number match
- "Hypertherm torch" ✅ Brand name + product type
- "220479" ✅ Manufacturer part number match

**Hybrid Search:**
- "Hypertherm gas torch" ✅ Combines brand recognition + semantic understanding
- "welding HYP220479" ✅ Combines product type + exact part number

## 📊 Streamlit UI Features

### Individual Search Mode
1. Select method from sidebar
2. Enter query
3. Click "Search with [Method]"
4. View results with field information

### Comparison Mode  
1. Enter query
2. Click "🔬 Compare All Methods"
3. View results in tabs:
   - **Comparison**: Side-by-side analysis
   - **Dense**: Results from description-only search
   - **BM25**: Results from keyword search
   - **MiniCOIL**: Results from neural sparse search
   - **Hybrid BM25**: Fusion results
   - **Hybrid MiniCOIL**: Neural fusion results

### Performance Analysis
- Search timing comparison
- Result count analysis
- Field-specific insights
- Score comparison across methods

## 🔍 Field-Specific Behavior

### Dense Vector Generation
```python
# Only from shortDescription_airgas_text
dense_text = product['shortDescription_airgas_text']
dense_embedding = dense_model.passage_embed([dense_text])
```

### Sparse Vector Generation  
```python
# From description + part numbers
sparse_text = ' '.join([
    product['shortDescription_airgas_text'],
    product['partNumber_airgas_text'], 
    product['manufacturerPartNumber_text']
])
sparse_embedding = sparse_model.passage_embed([sparse_text])
```

## ⚡ Performance Expectations

- **Dense Search**: 5-25ms (semantic matching)
- **BM25 Search**: 3-15ms (keyword matching)  
- **MiniCOIL Search**: 8-30ms (neural sparse)
- **Hybrid Search**: 15-50ms (parallel fusion)

## 🛠️ Troubleshooting

### Common Issues

1. **404 Errors**: Ensure the API service is running and indexing is complete
2. **No MiniCOIL Results**: Check if MiniCOIL model loaded successfully
3. **Slow Performance**: Verify collection is properly indexed with quantization
4. **Empty Results**: Check if the query matches available field content

### Debug Endpoints

Test service status:
```bash
curl http://localhost:8000/api/search/test
```

Get methods info:
```bash  
curl http://localhost:8000/api/search/methods-info
```

### Logs
Check service logs for initialization and search errors:
```bash
tail -f logs/service.log
```

## 🎯 Best Practices

1. **Use Dense** for semantic product discovery
2. **Use Sparse** for exact part number lookups
3. **Use Hybrid** for mixed queries requiring both semantic and exact matching
4. **Adjust fusion_alpha** based on whether you prefer semantic (higher alpha) or exact (lower alpha) results
5. **Monitor performance** and adjust result limits based on use case

This implementation provides comprehensive search capabilities with clear field separation and performance optimization for industrial product search.