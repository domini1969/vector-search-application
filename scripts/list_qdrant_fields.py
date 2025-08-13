#!/usr/bin/env python3
"""
Simple script to list field names using HTTP API
"""

import requests
import json
from collections import Counter

def check_qdrant_fields(collection_name="products", qdrant_url="http://localhost:6333", sample_size=10):
    """Check field names using HTTP API"""
    
    print(f"🔍 Analyzing collection: {collection_name}")
    print(f"📊 Sample size: {sample_size} documents")
    print("="*50)
    
    try:
        # Get collection info
        response = requests.get(f"{qdrant_url}/collections/{collection_name}")
        if response.status_code == 200:
            collection_info = response.json()["result"]
            print(f"📁 Collection status: {collection_info.get('status', 'unknown')}")
            print(f"📈 Total points: {collection_info.get('points_count', 0)}")
        else:
            print(f"❌ Failed to get collection info: {response.status_code}")
            return
        
        print()
        
        # Get sample points using scroll
        scroll_data = {
            "limit": sample_size,
            "with_payload": True
        }
        
        response = requests.post(
            f"{qdrant_url}/collections/{collection_name}/points/scroll",
            json=scroll_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get points: {response.status_code} - {response.text}")
            return
        
        data = response.json()
        points = data["result"]["points"]
        
        if not points:
            print("❌ No points found in collection")
            return
        
        print(f"✅ Retrieved {len(points)} points for analysis")
        print()
        
        # Analyze fields
        all_fields = Counter()
        field_samples = {}
        field_types = {}
        
        for point in points:
            payload = point.get("payload", {})
            for field_name, field_value in payload.items():
                all_fields[field_name] += 1
                
                # Track field types
                field_type = type(field_value).__name__
                if field_name not in field_types:
                    field_types[field_name] = field_type
                
                # Keep a sample value
                if field_name not in field_samples:
                    field_samples[field_name] = field_value
        
        # Display results
        print("📋 FIELD ANALYSIS:")
        print("="*90)
        print(f"{'Field Name':<40} {'Type':<10} {'Count':<8} {'Sample Value':<30}")
        print("-" * 90)
        
        for field_name, count in all_fields.most_common():
            field_type = field_types.get(field_name, 'unknown')
            sample_value = str(field_samples.get(field_name, ''))
            if len(sample_value) > 30:
                sample_value = sample_value[:27] + "..."
            
            print(f"{field_name:<40} {field_type:<10} {count:<8} {sample_value:<30}")
        
        print()
        print("🎯 SUMMARY:")
        print(f"• Total unique fields: {len(all_fields)}")
        print(f"• Documents analyzed: {len(points)}")
        
        # Check for image fields
        image_fields = [field for field in all_fields.keys() if 'img' in field.lower() or 'image' in field.lower()]
        if image_fields:
            print(f"🖼️  Image fields found: {', '.join(image_fields)}")
            for img_field in image_fields:
                sample_img = field_samples.get(img_field, 'N/A')
                print(f"   • {img_field}: {sample_img}")
        else:
            print("❌ No image fields found")
        
        # Check for ID fields
        id_fields = [field for field in all_fields.keys() if 'id' in field.lower() or field.startswith('_')]
        if id_fields:
            print(f"🆔 ID fields found: {', '.join(id_fields)}")
            for id_field in id_fields:
                sample_id = field_samples.get(id_field, 'N/A')
                print(f"   • {id_field}: {sample_id}")
        
        print()
        print("🔧 RECOMMENDED API CONFIGURATION:")
        
        # Suggest ID field
        if '_id' in all_fields:
            print(f"   id_field = '_id'  # ✅ Recommended")
        elif 'partNumber_airgas_text' in all_fields:
            print(f"   id_field = 'partNumber_airgas_text'")
        else:
            most_common_id = id_fields[0] if id_fields else list(all_fields.keys())[0]
            print(f"   id_field = '{most_common_id}'")
        
        # Show complete first document
        print()
        print("📄 FIRST COMPLETE DOCUMENT:")
        print("="*50)
        if points:
            sample_doc = points[0]["payload"]
            print(json.dumps(sample_doc, indent=2))
        
        return all_fields, field_samples
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Check Qdrant collection fields")
    parser.add_argument("--collection", default="products", help="Collection name")
    parser.add_argument("--url", default="http://localhost:6333", help="Qdrant URL")
    parser.add_argument("--sample-size", type=int, default=10, help="Number of documents to sample")
    
    args = parser.parse_args()
    
    check_qdrant_fields(args.collection, args.url, args.sample_size)