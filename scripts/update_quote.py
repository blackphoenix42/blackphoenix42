#!/usr/bin/env python3
import re
import random
import urllib.parse
import time
import pathlib
import requests
import json

# Fallback quotes in case web fetch fails - all with known authors
FALLBACK_QUOTES = [
    ("Premature optimization is the root of all evil.", "Donald Knuth"),
    ("Good judgment comes from experience, and experience comes from bad judgment.", "Fred Brooks"),
    ("Simplicity is a great virtue but it requires hard work to achieve it.", "Edsger Dijkstra"),
    ("If you do not work on an important problem, it's unlikely you'll do important work.", "Richard Hamming"),
    ("The most dangerous phrase in the language is: \"We've always done it this way.\"", "Grace Hopper"),
    ("Programs must be written for people to read, and only incidentally for machines to execute.", "Harold Abelson"),
    ("Make it work, make it right, make it fast.", "Kent Beck"),
    ("Code is like humor. When you have to explain it, it's bad.", "Cory House"),
    ("First, solve the problem. Then, write the code.", "John Johnson"),
    ("Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "Martin Fowler"),
    ("Experience is the name everyone gives to their mistakes.", "Oscar Wilde"),
    ("Java is to JavaScript what car is to Carpet.", "Chris Heilmann"),
    ("The best way to get a project done faster is to start sooner.", "Jim Highsmith"),
    ("Walking on water and developing software from a specification are easy if both are frozen.", "Edward V. Berard"),
    ("The most important property of a program is whether it accomplishes the intention of its user.", "C.A.R. Hoare"),
    ("Debugging is twice as hard as writing the code in the first place.", "Brian Kernighan"),
    ("Measuring programming progress by lines of code is like measuring aircraft building progress by weight.", "Bill Gates"),
    ("Talk is cheap. Show me the code.", "Linus Torvalds"),
    ("Programming isn't about what you know; it's about what you can figure out.", "Chris Pine"),
    ("The computer was born to solve problems that did not exist before.", "Bill Gates"),
    ("Software is a gas; it expands to fill its container.", "Nathan Myhrvold"),
    ("There are only two hard things in Computer Science: cache invalidation and naming things.", "Phil Karlton"),
    ("The function of good software is to make the complex appear to be simple.", "Grady Booch"),
    ("Fix the cause, not the symptom.", "Steve Maguire"),
    ("Simplicity is the ultimate sophistication.", "Leonardo da Vinci"),
    ("Before software can be reusable it first has to be usable.", "Ralph Johnson"),
    ("Make everything as simple as possible, but not simpler.", "Albert Einstein"),
    ("Code never lies, comments sometimes do.", "Ron Jeffries"),
    ("Given enough eyeballs, all bugs are shallow.", "Eric S. Raymond"),
    ("Don't comment bad code—rewrite it.", "Brian Kernighan"),
    ("A language that doesn't affect the way you think about programming is not worth knowing.", "Alan Perlis"),
    ("The best programs are written so that computing machines can perform them quickly and so that human beings can understand them clearly.", "Donald Knuth"),
    ("Programming is not about typing, it's about thinking.", "Rich Hickey"),
    ("The most disastrous thing that you can ever learn is your first programming language.", "Alan Kay"),
    ("Always code as if the guy who ends up maintaining your code will be a violent psychopath who knows where you live.", "John Woods"),
    ("Perfect is the enemy of good.", "Voltaire"),
    ("The only way to learn a new programming language is by writing programs in it.", "Dennis Ritchie"),
    ("Programs are meant to be read by humans and only incidentally for computers to execute.", "Donald Knuth"),
    ("A computer program does what you tell it to do, not what you want it to do.", "Grady Booch"),
    ("Testing can only prove the presence of bugs, not their absence.", "Edsger Dijkstra"),
    ("I'm not a great programmer; I'm just a good programmer with great habits.", "Kent Beck"),
    ("Software and cathedrals are much the same — first we build them, then we pray.", "Sam Redwine"),
    ("The trouble with programmers is that you can never tell what a programmer is doing until it's too late.", "Seymour Cray"),
    ("Most good programmers do programming not because they expect to get paid or get adulation by the public, but because it is fun to program.", "Linus Torvalds"),
    ("Learning to write programs stretches your mind, and helps you think better, creates a way of thinking about things that I think is helpful in all domains.", "Bill Gates"),
    ("Quality means doing it right when no one is looking.", "Henry Ford"),
    ("Innovation distinguishes between a leader and a follower.", "Steve Jobs"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("If you are not embarrassed by the first version of your product, you've launched too late.", "Reid Hoffman"),
    ("Move fast and break things. Unless you are breaking stuff, you are not moving fast enough.", "Mark Zuckerberg"),
    ("Your most unhappy customers are your greatest source of learning.", "Bill Gates"),
    ("Code is poetry.", "Steve McConnell"),
    ("Programs are meant to be read by humans and only incidentally for computers to execute.", "Harold Abelson"),
]

def fetch_programming_quotes():
    """Fetch programming quotes from multiple web sources."""
    quotes = []
    
    # Try multiple sources with different APIs
    sources = [
        # Quotable.io - Multiple categories
        {
            'url': 'https://api.quotable.io/random?tags=technology',
            'parser': lambda data: (data.get('content', ''), data.get('author', 'Unknown'))
        },
        {
            'url': 'https://api.quotable.io/random?tags=wisdom&minLength=30',
            'parser': lambda data: (data.get('content', ''), data.get('author', 'Unknown'))
        },
        {
            'url': 'https://api.quotable.io/random?tags=inspirational&minLength=20&maxLength=200',
            'parser': lambda data: (data.get('content', ''), data.get('author', 'Unknown'))
        },
        {
            'url': 'https://api.quotable.io/random?minLength=40&maxLength=180',
            'parser': lambda data: (data.get('content', ''), data.get('author', 'Unknown'))
        },
        # ZenQuotes API
        {
            'url': 'https://zenquotes.io/api/random',
            'parser': lambda data: (data[0].get('q', '') if isinstance(data, list) and len(data) > 0 else '', 
                                   data[0].get('a', 'Unknown') if isinstance(data, list) and len(data) > 0 else 'Unknown')
        },
        # QuoteGarden API
        {
            'url': 'https://quotegarden.herokuapp.com/api/v3/quotes/random',
            'parser': lambda data: (data.get('data', {}).get('quoteText', ''), 
                                   data.get('data', {}).get('quoteAuthor', 'Unknown'))
        },
        # Advice Slip API (repurposed for quotes)
        {
            'url': 'https://api.adviceslip.com/advice',
            'parser': lambda data: (data.get('slip', {}).get('advice', ''), 'Advice Slip')
        },
        # Programming Quotes API (if available)
        {
            'url': 'https://programming-quotes-api.herokuapp.com/quotes/random',
            'parser': lambda data: (data.get('en', ''), data.get('author', 'Unknown'))
        },
        # They Said So Quote API
        {
            'url': 'https://quotes.rest/qod?category=inspire',
            'parser': lambda data: (data.get('contents', {}).get('quotes', [{}])[0].get('quote', '') if data.get('contents', {}).get('quotes') else '',
                                   data.get('contents', {}).get('quotes', [{}])[0].get('author', 'Unknown') if data.get('contents', {}).get('quotes') else 'Unknown')
        }
    ]
    
    # Fetch multiple quotes for more variety
    for i in range(8):  # Try to fetch 8 quotes from different sources
        source = random.choice(sources)
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(source['url'], timeout=10, headers=headers)
            if response.status_code == 200:
                data = response.json()
                quote, author = source['parser'](data)
                
                # Filter out quotes with unknown authors and ensure meaningful content
                if (quote and author and 
                    len(quote.strip()) > 15 and 
                    author.strip().lower() not in ['unknown', 'anonymous', '', 'advice slip']):
                    quotes.append((quote.strip(), author.strip()))
                    print(f"Fetched quote {i+1}: '{quote[:50]}...' - {author}")
                else:
                    print(f"Skipped quote {i+1}: No author or too short")
                    
            time.sleep(0.2)  # Small delay to be respectful to the APIs
        except Exception as e:
            print(f"Failed to fetch quote {i+1} from {source['url']}: {e}")
            continue
    
    return quotes

def get_quotes():
    """Get a mix of web-fetched and fallback quotes."""
    web_quotes = fetch_programming_quotes()
    
    # Combine web quotes with fallback quotes for variety
    all_quotes = web_quotes + FALLBACK_QUOTES
    
    # Remove duplicates and filter out unknown authors
    seen_quotes = set()
    unique_quotes = []
    for quote, author in all_quotes:
        # Filter out quotes with unknown/anonymous authors
        if (quote.lower() not in seen_quotes and 
            author.strip().lower() not in ['unknown', 'anonymous', '', 'null', 'none']):
            seen_quotes.add(quote.lower())
            unique_quotes.append((quote, author))
    
    print(f"Total unique quotes with known authors: {len(unique_quotes)}")
    return unique_quotes

def main():
    """Main function to update README with a new quote."""
    THEME = "dark"   # try: dark, radical, merko, tokyonight, etc.
    
    # Get all available quotes (web + fallback)
    all_quotes = get_quotes()
    
    if not all_quotes:
        print("No quotes available!")
        return
    
    # Select a random quote
    q, author = random.choice(all_quotes)
    print(f"Selected quote: '{q}' - {author}")

    quote = urllib.parse.quote(q)
    auth = urllib.parse.quote(author)
    # cache-bust param so the image refreshes
    t = int(time.time())

    url = f"https://quotes-github-readme.vercel.app/api?type=horizontal&theme={THEME}&quote={quote}&author={auth}&t={t}"
    block = f'''<div align="center">
  <img src="{url}" alt="Quote"/>
</div>'''

    readme_path = pathlib.Path("README.md")
    
    try:
        text = readme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print("README.md not found!")
        return

    start = "<!-- QUOTE:START -->"
    end = "<!-- QUOTE:END -->"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.DOTALL)

    new_section = f"{start}\n{block}\n{end}"
    new_text = pattern.sub(new_section, text)

    if new_text != text:
        readme_path.write_text(new_text, encoding="utf-8")
        print("README updated with a new quote.")
    else:
        print("README unchanged (no marker found or same content).")

if __name__ == "__main__":
    main()