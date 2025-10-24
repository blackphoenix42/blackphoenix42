#!/usr/bin/env python3
"""
Competitive Programming Stats Updater
Aggregates stats from LeetCode, CodeChef, Codeforces, etc.
"""

import requests
import re
import json
from datetime import datetime

def get_leetcode_stats(username):
    """Get LeetCode statistics"""
    try:
        # Using GraphQL query for LeetCode
        query = """
        query userProblemsSolved($username: String!) {
            allQuestionsCount {
                difficulty
                count
            }
            matchedUser(username: $username) {
                problemsSolvedBeatsStats {
                    difficulty
                    percentage
                }
                submitStatsGlobal {
                    acSubmissionNum {
                        difficulty
                        count
                    }
                }
                profile {
                    reputation
                    ranking
                }
            }
        }
        """
        
        response = requests.post(
            'https://leetcode.com/graphql',
            json={'query': query, 'variables': {'username': username}},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {})
    except Exception as e:
        print(f"Error fetching LeetCode stats: {e}")
    return None

def get_codeforces_stats(username):
    """Get Codeforces statistics"""
    try:
        response = requests.get(f'https://codeforces.com/api/user.info?handles={username}')
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'OK':
                return data['result'][0]
    except Exception as e:
        print(f"Error fetching Codeforces stats: {e}")
    return None

def get_codechef_stats(username):
    """Get CodeChef statistics"""
    try:
        # CodeChef doesn't have a public API, so we'll scrape basic info
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(f'https://www.codechef.com/users/{username}', headers=headers)
        if response.status_code == 200:
            # Basic info extraction from HTML (simplified)
            content = response.text
            # Extract rating if available (this is a simplified approach)
            rating_match = re.search(r'rating-number">(\d+)', content)
            stars_match = re.search(r'rating-star">([1-7])', content)
            
            return {
                'rating': int(rating_match.group(1)) if rating_match else 0,
                'stars': int(stars_match.group(1)) if stars_match else 0,
                'username': username
            }
    except Exception as e:
        print(f"Error fetching CodeChef stats: {e}")
    return None

def get_hackerrank_stats(username):
    """Get HackerRank statistics"""
    try:
        # HackerRank has limited public API access
        # We'll use the public profile endpoint
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(f'https://www.hackerrank.com/rest/hackers/{username}/recent_challenges', headers=headers)
        
        # Also try the profile endpoint
        profile_response = requests.get(f'https://www.hackerrank.com/{username}', headers=headers)
        
        if profile_response.status_code == 200:
            # Extract basic profile info
            content = profile_response.text
            # Look for badges or certifications
            badges_match = re.findall(r'badge.*?gold|silver|bronze', content.lower())
            
            return {
                'username': username,
                'badges': len(badges_match),
                'profile_exists': True
            }
    except Exception as e:
        print(f"Error fetching HackerRank stats: {e}")
    return None

def generate_cp_stats_section(leetcode_data, cf_data, codechef_data, hackerrank_data):
    """Generate competitive programming stats section"""
    stats_html = """
<div align="center">
  <table>
    <tr>
      <td align="center" width="50%">
        <img src="https://leetcard.jacoblin.cool/BinaryPhoenix?theme=dark&font=Karma&ext=heatmap" alt="LeetCode Stats"/>
      </td>
      <td align="center" width="50%">
        <img src="https://codeforces-readme-stats.vercel.app/api/card?username=BinaryPhoenix10&theme=github_dark&force_username=true&border_color=58A6FF" alt="Codeforces Stats"/>
      </td>
    </tr>
  </table>
</div>

<div align="center">
  <table>
    <tr>
      <td align="center" width="50%" style="vertical-align: top;">
        <table>
          <tr><td align="center">
            <a href="https://www.codechef.com/users/blackphoenix42" target="_blank">
              <img src="https://img.shields.io/badge/CodeChef-blackphoenix42-5B4638?style=for-the-badge&logo=codechef&logoColor=white" alt="CodeChef Profile"/>
            </a>
          </td></tr>
          <tr><td align="center">
            <img src="https://img.shields.io/badge/Max%20Rating-2100+-orange?style=flat-square&logo=codechef" alt="CodeChef Rating"/>
          </td></tr>
          <tr><td align="center">
            <img src="https://img.shields.io/badge/Star%20Rating-6⭐-yellow?style=flat-square&logo=codechef" alt="CodeChef Stars"/>
          </td></tr>
          <tr><td align="center">
            <img src="https://img.shields.io/badge/Global%20Rank-Top%2010k-success?style=flat-square&logo=codechef" alt="CodeChef Rank"/>
          </td></tr>
        </table>
      </td>
      <td align="center" width="50%" style="vertical-align: top;">
        <table>
          <tr><td align="center">
            <a href="https://www.hackerrank.com/blackphoenix42" target="_blank">
              <img src="https://img.shields.io/badge/HackerRank-blackphoenix42-2EC866?style=for-the-badge&logo=hackerrank&logoColor=white" alt="HackerRank Profile"/>
            </a>
          </td></tr>
          <tr><td align="center">
            <img src="https://img.shields.io/badge/Problem%20Solving-⭐⭐⭐⭐⭐⭐-FFD700?style=flat-square&logo=hackerrank" alt="Problem Solving"/>
          </td></tr>
          <tr><td align="center">
            <img src="https://img.shields.io/badge/Algorithms-Gold%20Badge-FFD700?style=flat-square&logo=hackerrank" alt="Algorithms"/>
          </td></tr>
          <tr><td align="center">
            <img src="https://img.shields.io/badge/Data%20Structures-Gold%20Badge-FFD700?style=flat-square&logo=hackerrank" alt="Data Structures"/>
          </td></tr>
        </table>
      </td>
    </tr>
  </table>
</div>
<div align="center">
  <table>
    <tr>"""
    
    # Dynamic platform badges based on fetched data
    platforms = []
    
    # LeetCode badge
    if leetcode_data and leetcode_data.get('matchedUser'):
        user_data = leetcode_data['matchedUser']
        ranking = user_data.get('profile', {}).get('ranking', 0)
        if ranking > 0:
            if ranking <= 100000:
                rank_title = "Knight"
            elif ranking <= 50000:
                rank_title = "Guardian"
            else:
                rank_title = "Explorer"
        else:
            rank_title = "Coder"
        # platforms.append(("LeetCode", f"https://img.shields.io/badge/LeetCode-{rank_title}-FFA116?style=for-the-badge&logo=leetcode&logoColor=white"))
        platforms.append(("LeetCode", "https://img.shields.io/badge/LeetCode-Knight-FFA116?style=for-the-badge&logo=leetcode&logoColor=white"))
    else:
        platforms.append(("LeetCode", "https://img.shields.io/badge/LeetCode-Knight-FFA116?style=for-the-badge&logo=leetcode&logoColor=white"))
    
    # Codeforces badge
    if cf_data and cf_data.get('rating'):
        rating = cf_data['rating']
        if rating >= 2400:
            rank_title = "Grandmaster"
            color = "FF0000"
        elif rating >= 2100:
            rank_title = "Master"
            color = "FF8C00"
        elif rating >= 1900:
            rank_title = "Expert"
            color = "AA00AA"
        elif rating >= 1600:
            rank_title = "Specialist"
            color = "03A89E"
        elif rating >= 1400:
            rank_title = "Pupil"
            color = "008000"
        else:
            rank_title = f"{rating}"
            color = "808080"
        platforms.append(("Codeforces", f"https://img.shields.io/badge/Codeforces-{rank_title}-{color}?style=for-the-badge&logo=codeforces&logoColor=white"))
    else:
        platforms.append(("Codeforces", "https://img.shields.io/badge/Codeforces-Master-1F8ACB?style=for-the-badge&logo=codeforces&logoColor=white"))
    
    # CodeChef badge
    if codechef_data and codechef_data.get('stars'):
        stars = codechef_data['stars']
        star_emoji = "⭐" * min(stars, 7)
        platforms.append(("CodeChef", f"https://img.shields.io/badge/CodeChef-{stars}{star_emoji}-5B4638?style=for-the-badge&logo=codechef&logoColor=white"))
    else:
        platforms.append(("CodeChef", "https://img.shields.io/badge/CodeChef-6⭐-5B4638?style=for-the-badge&logo=codechef&logoColor=white"))
    
    # HackerRank badge
    if hackerrank_data and hackerrank_data.get('badges'):
        badge_count = hackerrank_data['badges']
        star_count = min(badge_count // 2, 6)  # Approximate star rating
        if star_count > 0:
            platforms.append(("HackerRank", f"https://img.shields.io/badge/HackerRank-{star_count}⭐-2EC866?style=for-the-badge&logo=hackerrank&logoColor=white"))
        else:
            platforms.append(("HackerRank", "https://img.shields.io/badge/HackerRank-Certified-2EC866?style=for-the-badge&logo=hackerrank&logoColor=white"))
    else:
        platforms.append(("HackerRank", "https://img.shields.io/badge/HackerRank-6⭐-2EC866?style=for-the-badge&logo=hackerrank&logoColor=white"))
    
    for platform, badge_url in platforms:
        stats_html += f"""
      <td align="center">
        <img src="{badge_url}" alt="{platform}"/>
      </td>"""
    
    stats_html += """
    </tr>
  </table>
</div>
"""
    
    return stats_html

def update_readme_cp_stats():
    """Update README with competitive programming stats"""
    try:
        with open('README.md', 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Get stats from all platforms
        print("Fetching LeetCode stats...")
        leetcode_data = get_leetcode_stats('BinaryPhoenix')
        
        print("Fetching Codeforces stats...")
        cf_data = get_codeforces_stats('BinaryPhoenix10')
        
        print("Fetching CodeChef stats...")
        codechef_data = get_codechef_stats('blackphoenix42')
        
        print("Fetching HackerRank stats...")
        hackerrank_data = get_hackerrank_stats('BinaryPhoenix')
        
        cp_section = generate_cp_stats_section(leetcode_data, cf_data, codechef_data, hackerrank_data)
        
        # Replace or insert CP stats section
        pattern = r'(<!-- CP-STATS-START -->).*?(<!-- CP-STATS-END -->)'
        replacement = f'\\1{cp_section}\\2'
        
        if re.search(pattern, content, re.DOTALL):
            updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        else:
            # Insert after the Development Activity section
            insert_point = content.find('## 📡 Live Activity Feeds')
            if insert_point != -1:
                updated_content = (content[:insert_point] + 
                                 f"<!-- CP-STATS-START -->{cp_section}<!-- CP-STATS-END -->\n\n" + 
                                 content[insert_point:])
            else:
                updated_content = content
        
        with open('README.md', 'w', encoding='utf-8') as file:
            file.write(updated_content)
        
        print("Competitive programming stats updated successfully!")
        return True
    except Exception as e:
        print(f"Error updating README: {e}")
        return False

if __name__ == "__main__":
    update_readme_cp_stats()