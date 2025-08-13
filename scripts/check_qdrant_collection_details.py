#!/usr/bin/env python3
"""
Ultra Simple Collection Check - Bypasses Pydantic issues
"""

import requests
import json

def check_collections_http():
    """Use direct HTTP calls to avoid Pydantic issues"""
    
    print("🔍 ULTRA SIMPLE COLLECTION CHECK")
    print("="*40)
    
    try:
        # Get collections list via HTTP
        response = requests.get("http://localhost:6333/collections", timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Error: HTTP {response.status_code}")
            return
        
        data = response.json()
        collections = data.get("result", {}).get("collections", [])
        
        print(f"📊 Found {len(collections)} collections:\n")
        
        for i, collection in enumerate(collections, 1):
            name = collection.get("name", "unknown")
            print(f"[{i}] {name}")
            
            # Get collection details
            try:
                detail_response = requests.get(f"http://localhost:6333/collections/{name}", timeout=10)
                
                if detail_response.status_code == 200:
                    detail_data = detail_response.json()
                    result = detail_data.get("result", {})
                    
                    # Get point count
                    points_count = result.get("points_count", 0)
                    status = result.get("status", "unknown")
                    
                    print(f"    Points: {points_count:,}")
                    print(f"    Status: {status}")
                    
                    # Check if it has data
                    if points_count > 0:
                        print(f"    ✅ Has data!")
                    else:
                        print(f"    ❌ Empty")
                    
                    # Try to check vector config (basic)
                    config = result.get("config", {})
                    params = config.get("params", {})
                    vectors = params.get("vectors", {})
                    
                    if isinstance(vectors, dict) and "dense" in vectors:
                        print(f"    ✅ Has 'dense' vectors (compatible)")
                    elif vectors:
                        vector_names = list(vectors.keys()) if isinstance(vectors, dict) else ["unknown"]
                        print(f"    🔧 Vectors: {vector_names}")
                    else:
                        print(f"    ❓ Vector config unclear")
                        
                else:
                    print(f"    ❌ Error getting details: HTTP {detail_response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Error: {str(e)[:50]}...")
            
            print()
        
        print("🎯 TARGET COLLECTION SUMMARY:")
        print("-" * 30)
        
        # Check specific collections
        targets = ["products_fast", "products_fast_asymmetric"]
        recommendations = []
        
        for target in targets:
            found = False
            
            for collection in collections:
                if collection.get("name") == target:
                    found = True
                    
                    try:
                        detail_response = requests.get(f"http://localhost:6333/collections/{target}", timeout=10)
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            points_count = detail_data.get("result", {}).get("points_count", 0)
                            
                            print(f"✅ {target}: {points_count:,} points")
                            
                            if points_count > 0:
                                recommendations.append((target, points_count))
                            
                        else:
                            print(f"❌ {target}: Error accessing")
                    except:
                        print(f"❌ {target}: Error")
                    break
            
            if not found:
                print(f"❌ {target}: NOT FOUND")
        
        print("\n💡 RECOMMENDATION:")
        print("-" * 15)
        
        if recommendations:
            # Sort by point count
            recommendations.sort(key=lambda x: x[1], reverse=True)
            best_collection, best_count = recommendations[0]
            
            print(f"🎯 USE: '{best_collection}'")
            print(f"   Has {best_count:,} points")
            print(f"\n🔧 UPDATE YOUR SEARCH SERVICE:")
            print(f"   Change collection name from 'products_fast' to '{best_collection}'")
            
        else:
            print("❌ No collections with data found!")
            print("   Check if your indexing completed successfully")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Qdrant at http://localhost:6333")
        print("   Make sure Qdrant is running")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_with_working_search_client():
    """Use your working search client code to check collections"""
    
    print("\n" + "="*40)
    print("🔍 USING YOUR WORKING SEARCH CLIENT")
    print("="*40)
    
    try:
        # Import your working client
        from qdrant_client import QdrantClient
        
        client = QdrantClient("localhost", port=6333, timeout=60, prefer_grpc=True)
        
        # Try to count points in each collection directly
        test_collections = ["products_fast", "products_fast_asymmetric"]
        
        for collection_name in test_collections:
            try:
                # Use the same method as your working test script
                results, _ = client.scroll(
                    collection_name=collection_name,
                    limit=1,  # Just get 1 point to test
                    with_payload=False,
                    with_vectors=False
                )
                
                print(f"✅ {collection_name}: EXISTS and accessible")
                
                # Try to get more info
                try:
                    # Simple count using scroll with high limit
                    all_results, _ = client.scroll(
                        collection_name=collection_name,
                        limit=100000,  # High limit to get rough count
                        with_payload=False,
                        with_vectors=False
                    )
                    
                    count = len(all_results)
                    print(f"   ~{count:,} points (sample)")
                    
                    if count > 0:
                        print(f"   ✅ HAS DATA - Use this collection!")
                    else:
                        print(f"   ❌ Empty")
                        
                except Exception as e:
                    print(f"   Count check failed: {e}")
                
            except Exception as e:
                if "not found" in str(e).lower():
                    print(f"❌ {collection_name}: NOT FOUND")
                else:
                    print(f"❌ {collection_name}: Error - {str(e)[:50]}...")
        
    except Exception as e:
        print(f"❌ Client check failed: {e}")

if __name__ == "__main__":
    # Try HTTP method first
    check_collections_http()
    
    # Try using working client method
    check_with_working_search_client()