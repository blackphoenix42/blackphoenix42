#!/usr/bin/env python3
"""
README Health Checker
Validates links, images, and content in README.md
"""

import requests
import re
import concurrent.futures
from urllib.parse import urlparse
from datetime import datetime

def check_url(url, timeout=10):
    """Check if a URL is accessible"""
    try:
        # Skip data URLs and local URLs
        if url.startswith('data:') or url.startswith('#'):
            return {'url': url, 'status': 'skipped', 'reason': 'data/anchor url'}
        
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        if response.status_code == 405:  # Method not allowed, try GET
            response = requests.get(url, timeout=timeout, stream=True)
        
        return {
            'url': url,
            'status': 'ok' if response.status_code < 400 else 'error',
            'status_code': response.status_code,
            'reason': response.reason if response.status_code >= 400 else None
        }
    except requests.exceptions.Timeout:
        return {'url': url, 'status': 'timeout', 'reason': 'Request timeout'}
    except requests.exceptions.ConnectionError:
        return {'url': url, 'status': 'connection_error', 'reason': 'Connection failed'}
    except Exception as e:
        return {'url': url, 'status': 'error', 'reason': str(e)}

def extract_urls_from_readme():
    """Extract all URLs from README.md"""
    try:
        with open('README.md', 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Extract URLs from markdown links and image sources
        link_pattern = r'\[([^\]]*)\]\(([^)]+)\)'
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        
        links = re.findall(link_pattern, content)
        images = re.findall(img_pattern, content)
        
        urls = []
        for text, url in links:
            urls.append({'type': 'link', 'text': text, 'url': url})
        
        for url in images:
            urls.append({'type': 'image', 'text': '', 'url': url})
        
        return urls
    except Exception as e:
        print(f"Error reading README.md: {e}")
        return []

def generate_health_report(url_results):
    """Generate a health report"""
    total_urls = len(url_results)
    ok_urls = sum(1 for result in url_results if result['status'] == 'ok')
    error_urls = [result for result in url_results if result['status'] not in ['ok', 'skipped']]
    
    report = f"""
# README Health Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

## Summary
- ✅ Total URLs checked: {total_urls}
- ✅ Working URLs: {ok_urls}
- ❌ Broken URLs: {len(error_urls)}
- ⚠️ Health Score: {(ok_urls/total_urls*100):.1f}%

"""
    
    if error_urls:
        report += "## ❌ Broken URLs\n\n"
        for result in error_urls:
            report += f"- **{result['status'].upper()}**: {result['url']}\n"
            if result.get('reason'):
                report += f"  - Reason: {result['reason']}\n"
            report += "\n"
    
    report += "## ✅ Status Details\n\n"
    status_counts = {}
    for result in url_results:
        status = result['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        report += f"- {status.upper()}: {count}\n"
    
    return report

def check_readme_health():
    """Main function to check README health"""
    print("Extracting URLs from README.md...")
    url_data = extract_urls_from_readme()
    
    if not url_data:
        print("No URLs found in README.md")
        return
    
    urls = [item['url'] for item in url_data]
    unique_urls = list(set(urls))  # Remove duplicates
    
    print(f"Found {len(urls)} URLs ({len(unique_urls)} unique)")
    print("Checking URL accessibility...")
    
    # Check URLs concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(check_url, unique_urls))
    
    # Generate and save report
    report = generate_health_report(results)
    
    with open('readme_health_report.md', 'w', encoding='utf-8') as file:
        file.write(report)
    
    print("Health check complete! Report saved to readme_health_report.md")
    
    # Print summary
    error_count = sum(1 for r in results if r['status'] not in ['ok', 'skipped'])
    if error_count == 0:
        print("🎉 All URLs are working!")
    else:
        print(f"⚠️ Found {error_count} broken URLs")

if __name__ == "__main__":
    check_readme_health()