#!/usr/bin/env python3
"""
Limerita Deep Research - Single Pass with Multi-Agent Counsel + Voting
"""
import requests
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Optional
from flask import Flask, Response, jsonify, request, send_from_directory
from flask_cors import CORS
import threading
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse, urljoin
from collections import deque
import time
import ast
import concurrent.futures
import random
import logging

app = Flask(__name__)
CORS(app)

# Suppress Flask's default request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

research_state = {
    'is_researching': False,
    'progress': 0,
    'current_agent': '',
    'results': [],
    'sources': [],
    'votes': []
}

class WebSearchEngine:
    """Real web search engine with multiple methods"""
   
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
   
    def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Search using multiple methods"""
        print(f"\n Searching for: {query}")
       
        results = self._search_duckduckgo_api(query, max_results)
        if results:
            print(f" Found {len(results)} results via DDG API")
            return results
       
        results = self._search_duckduckgo_html(query, max_results)
        if results:
            print(f" Found {len(results)} results via DDG HTML")
            return results
       
        print(f"→ Using curated sources")
        return self._generate_curated_sources(query, max_results)
   
    def _search_duckduckgo_api(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Try DuckDuckGo Instant Answer API"""
        try:
            api_url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
            response = self.session.get(api_url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                return []
                
            data = response.json()
            results = []
           
            for topic in data.get('RelatedTopics', [])[:max_results]:
                if isinstance(topic, dict) and 'FirstURL' in topic:
                    results.append({
                        'title': topic.get('Text', 'Related Result'),
                        'url': topic['FirstURL'],
                        'snippet': topic.get('Text', '')[:200]
                    })
           
            return results
        except Exception as e:
            print(f"⚠ DDG API error: {str(e)}")
            return []
   
    def _search_duckduckgo_html(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Scrape DuckDuckGo HTML results"""
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = self.session.get(search_url, timeout=10, allow_redirects=True)
            
            if response.status_code != 200:
                return []
           
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
           
            result_divs = (soup.find_all('div', class_='result') or
                          soup.find_all('div', class_='results_links') or
                          soup.find_all('div', class_='web-result'))
           
            for result_div in result_divs[:max_results]:
                try:
                    link = (result_div.find('a', class_='result__a') or
                           result_div.find('a', class_='result__url') or
                           result_div.find('a'))
                   
                    if link:
                        url = link.get('href', '')
                        title = link.get_text(strip=True) or 'Search Result'
                       
                        snippet_elem = result_div.find('a', class_='result__snippet')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                       
                        if url and not url.startswith('http'):
                            if url.startswith('//'):
                                url = 'https:' + url
                            else:
                                continue
                       
                        if url and 'http' in url:
                            results.append({
                                'title': title,
                                'url': url,
                                'snippet': snippet
                            })
                except:
                    continue
           
            return results
        except Exception as e:
            print(f"⚠ DDG HTML error: {str(e)}")
            return []
   
    def _generate_curated_sources(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Generate curated, real sources based on query"""
        query_lower = query.lower()
        scholar_query = quote_plus(query)
       
        sources = [
            {'title': f'{query} - Wikipedia', 'url': f'https://en.wikipedia.org/w/index.php?search={scholar_query}', 'snippet': f'Wikipedia search for {query}'},
            {'title': f'Academic research on {query}', 'url': f'https://scholar.google.com/scholar?q={scholar_query}', 'snippet': f'Scholarly articles about {query}'},
            {'title': f'{query} - Britannica', 'url': f'https://www.britannica.com/search?query={scholar_query}', 'snippet': 'Encyclopedia search'},
            {'title': f'{query} discussions', 'url': f'https://www.reddit.com/search/?q={scholar_query}', 'snippet': 'Community discussions'},
        ]
       
        if 'code' in query_lower or 'programming' in query_lower:
            sources += [
                {'title': f'{query} - Stack Overflow', 'url': f'https://stackoverflow.com/search?q={scholar_query}', 'snippet': 'Programming Q&A'},
                {'title': f'{query} - GitHub', 'url': f'https://github.com/search?q={scholar_query}', 'snippet': 'Code repositories'},
            ]
       
        return sources[:max_results]
   
    def fetch_page_content(self, url: str, max_length: int = 3000, retries: int = 3) -> Optional[Dict[str, any]]:
        """Fetch and extract main content and links from a webpage"""
        for attempt in range(retries):
            try:
                print(f" Fetching: {url}")
                response = self.session.get(url, timeout=30, allow_redirects=True)
                
                if response.status_code == 429:
                    print(f" Rate limited - waiting 10s...")
                    time.sleep(10)
                    continue
                    
                if response.status_code != 200:
                    print(f"⚠ Status {response.status_code}")
                    return None
               
                soup = BeautifulSoup(response.text, 'html.parser')
               
                for elem in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                    elem.decompose()
               
                main_content = (
                    soup.find('main') or
                    soup.find(attrs={'role': 'main'}) or
                    soup.find('article') or
                    soup.find('div', class_=re.compile(r'(content|main|body|article)')) or
                    soup.body
                )
               
                text = main_content.get_text(separator=' ', strip=True) if main_content else soup.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text)
               
                if len(text) > max_length:
                    text = text[:max_length] + "..."
               
                base_domain = urlparse(url).netloc
                links = []
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    full_url = urljoin(url, href)
                    link_domain = urlparse(full_url).netloc
                    if full_url.startswith('http') and link_domain == base_domain:
                        links.append(full_url)
                links = list(set(links))[:30]
                
                print(f"✓ Extracted {len(text)} chars, {len(links)} links")
                return {'content': text, 'links': links}
                
            except Exception as e:
                print(f"⚠ Error fetching {url}: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(5)
                    
        return None

class OllamaClient:
    """Client for interacting with Ollama API"""
   
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
   
    def list_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return []
        except:
            return []
   
    def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        """Generate response from model"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        if system:
            payload["system"] = system
       
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=300
            )
            if response.status_code == 200:
                return response.json().get('response', '')
            return f"Error: Status {response.status_code}"
        except Exception as e:
            return f"Error: {e}"

class MemoryManager:
    """Manages persistent memory in memory.json"""
   
    def __init__(self, filepath: str = "memory.json"):
        self.filepath = filepath
        self.memory = self.load_memory()
   
    def load_memory(self) -> Dict:
        """Load memory from file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                return self._create_default_memory()
        return self._create_default_memory()
   
    def _create_default_memory(self) -> Dict:
        """Create default memory structure"""
        return {
            "user_profile": {
                "interests": [],
                "previous_topics": [],
                "preferences": {},
                "last_updated": None
            },
            "conversations": [],
            "research_sessions": [],
            "sources": [],
            "findings": [],
            "knowledge_base": {}
        }
   
    def save_memory(self):
        """Save memory to file"""
        with open(self.filepath, 'w') as f:
            json.dump(self.memory, f, indent=2)
   
    def add_research_session(self, topic: str, agents: List[str]):
        """Start new research session"""
        session = {
            "id": len(self.memory["research_sessions"]) + 1,
            "topic": topic,
            "agents": agents,
            "timestamp": datetime.now().isoformat(),
            "findings": [],
            "sources": []
        }
        self.memory["research_sessions"].append(session)
        
        if topic not in self.memory["user_profile"]["previous_topics"]:
            self.memory["user_profile"]["previous_topics"].append(topic)
        if topic not in self.memory["user_profile"]["interests"]:
            self.memory["user_profile"]["interests"].append(topic)
        self.memory["user_profile"]["last_updated"] = datetime.now().isoformat()
        
        self.save_memory()
        return session["id"]
   
    def add_finding(self, session_id: int, agent: str, finding: str, sources: List[str]):
        """Add research finding to session"""
        for session in self.memory["research_sessions"]:
            if session["id"] == session_id:
                session["findings"].append({
                    "agent": agent,
                    "content": finding,
                    "timestamp": datetime.now().isoformat()
                })
                session["sources"].extend(sources)
                session["sources"] = list(set(session["sources"]))
                
                self.memory["sources"].extend(sources)
                self.memory["sources"] = list(set(self.memory["sources"]))
                break
        self.save_memory()
   
    def get_user_context(self) -> str:
        """Get formatted user context"""
        context = "USER CONTEXT:\n"
        if self.memory["user_profile"]["previous_topics"]:
            context += f"Previous topics: {', '.join(self.memory['user_profile']['previous_topics'][-5:])}\n"
        if self.memory["user_profile"]["interests"]:
            context += f"Interests: {', '.join(self.memory['user_profile']['interests'])}\n"
        return context

class ChatManager:
    """Manages past chats in chats.json"""
   
    def __init__(self, filepath: str = "chats.json"):
        self.filepath = filepath
        self.chats = self.load_chats()
   
    def load_chats(self) -> List[Dict]:
        """Load chats from file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
   
    def save_chats(self):
        """Save chats to file"""
        with open(self.filepath, 'w') as f:
            json.dump(self.chats, f, indent=2)
   
    def add_chat(self, topic: str, mode: str, num_members: int, results: List[Dict], sources: List[str], votes: List[Dict] = None):
        """Add a completed research chat"""
        chat = {
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "mode": mode,
            "num_members": num_members if mode == 'counsel' else 0,
            "results": results,
            "sources": sources,
            "votes": votes or []
        }
        self.chats.append(chat)
        self.save_chats()

def repair_json(json_str: str) -> Dict:
    """Enhanced JSON repair"""
    try:
        return json.loads(json_str)
    except:
        json_str = re.sub(r'<think>.*?</think>', '', json_str, flags=re.DOTALL | re.IGNORECASE)
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            json_str = match.group(0)
        json_str = re.sub(r'(\w+):', r'"\1":', json_str)
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*\]', ']', json_str)
        try:
            return json.loads(json_str)
        except:
            return {}

class ResearchEngine:
    """Core research engine - single pass web research"""
   
    def __init__(self, ollama_client: OllamaClient, search_engine: WebSearchEngine):
        self.ollama = ollama_client
        self.search = search_engine
   
    def conduct_deep_research(self, topic: str, model: str, max_depth: int = 3, max_pages: int = 50) -> tuple[str, List[str]]:
        """Single deep research pass with BFS"""
        print(f"\n STARTING deep research on: \n {topic}")
        
        search_results = self.search.search(topic, max_results=10)
        
        if not search_results:
            return "No search results found.", []
       
        to_visit = deque([(result['url'], 1) for result in search_results])
        visited = set()
        all_sources = []
        research_content = ""
        
        page_count = 0
        
        while to_visit and page_count < max_pages:
            url, depth = to_visit.popleft()
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            all_sources.append(url)
            page_count += 1
            
            print(f" [{page_count}/{max_pages}] Depth {depth}: {url}")
            
            page_data = self.search.fetch_page_content(url)
            if not page_data:
                continue
            
            for link in page_data['links']:
                if link not in all_sources:
                    all_sources.append(link)
            
            system_prompt = f"""You are a research synthesizer. Integrate new information into the existing research summary.
Rules:
1. Use ONLY the new content provided
2. Keep output concise (3-5 paragraphs)
3. NO fake sources or URLs in output but let us know what information you are referencing if applicable.
4. Focus on factual synthesis"""
            
            prompt = f"""Topic: {topic}
Current summary: {research_content if research_content else 'Begin synthesis with this content.'}
New content: {page_data['content'][:2000]}

Synthesize this information into the summary."""
            
            research_content = self.ollama.generate(model, prompt, system_prompt)
            
            # Get follow-up links
            if page_data['links']:
                followup_prompt = f"""Topic: {topic}
Summary: {research_content[:1000]}
Links: {', '.join(page_data['links'][:50])}

Select 0-20 most relevant URLs for deeper research. Output ONLY JSON: {{"followups": ["url1", "url2"]}}"""
                
                followup_response = self.ollama.generate(model, followup_prompt, "Output only valid JSON, no other text.")
                followups = repair_json(followup_response).get('followups', [])
                
                for url in followups:
                    if isinstance(url, str) and url.startswith('http') and url not in visited:
                        to_visit.append((url, depth + 1))
       
        # Final polish
        if research_content:
            final_prompt = f"Use this research summary on {topic}: {research_content}"
            research_content = self.ollama.generate(model, final_prompt, "Create coherent, factual summary. NO fake sources in text. Dont just focus on one platform. Focus on the resources provided from reddit, wikipedia, britannica, ect..")
       
        all_sources = list(dict.fromkeys(all_sources))
        print(f"\n✓ Research complete: {len(all_sources)} sources")
        return research_content, all_sources

class CounselMember:
    """Individual counsel member that analyzes research"""
   
    def __init__(self, name: str, perspective: str, model: str, ollama: OllamaClient):
        self.name = name
        self.perspective = perspective
        self.model = model
        self.ollama = ollama
   
    def analyze(self, topic: str, research_data: str, sources: List[str]) -> str:
        """Analyze research from this counsel member's perspective"""
        print(f"\n {self.name} analyzing...")
        print(f" Research data length: {len(research_data)} chars")
        print(f" Number of sources available: {len(sources)}")
        print(f" First 500 chars of research:\n{research_data[:500]}...")
        
        system_prompt = f"""You are {self.name}, a counsel member with expertise in {self.perspective}.
IMPORTANT RULES - FOLLOW STRICTLY:
- Base your ENTIRE analysis ONLY on the provided research findings and sources.
- Stay strictly on-topic: Discuss ONLY the {topic}. Do NOT introduce unrelated topics, examples, or diversions.
- Weigh in on the meaning and implications of the research from your perspective.
- Reference key points from the research and indicate they come from the gathered sources (e.g., 'Based on the researched data...') without listing URLs or specific sources.
- Be concise: 2-4 paragraphs of insightful analysis.
- No hallucinations: Do not add information not in the research.
- Dont just focus on one platform(eg. wikipedia) from the research, look at all that we found and use it wisely. 
- If the research lacks info for your perspective, state that clearly."""
        
        prompt = f"""Topic: {topic}

Research Findings (gathered from {len(sources)} sources):
{research_data}

Based solely on this research, provide your expert opinion from the {self.perspective} viewpoint.
What is the meaning of these findings? Key insights? Implications? Always tie back to the provided research data."""
        
        print(f" Sending prompt to {self.name}...")
        analysis = self.ollama.generate(self.model, prompt, system_prompt)
        print(f"✓ {self.name} analysis complete ({len(analysis)} chars)")
        return analysis

class ResearchCounsel:
    """Manages single-pass research with multi-agent counsel"""
   
    def __init__(self, model: str, ollama_client: OllamaClient, memory: MemoryManager, chat_manager: ChatManager):
        self.model = model
        self.ollama = ollama_client
        self.memory = memory
        self.chat_manager = chat_manager
        self.search = WebSearchEngine()
        self.research_engine = ResearchEngine(ollama_client, self.search)
   
    def conduct_research_single(self, topic: str) -> Dict:
        """Single-pass research without counsel"""
        global research_state
        
        research_state['is_researching'] = True
        research_state['progress'] = 10
        research_state['current_agent'] = ' Deep Research in Progress...'
        research_state['results'] = []
        research_state['sources'] = []
        research_state['votes'] = []
        
        user_context = self.memory.get_user_context()
        session_id = self.memory.add_research_session(topic, ["Single Pass Researcher"])
        
        research_state['progress'] = 50
        findings, sources = self.research_engine.conduct_deep_research(topic, self.model)
        
        result = {
            'agent': ' Research Summary',
            'content': findings,
            'sources': sources,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        
        research_state['results'].append(result)
        research_state['sources'] = sources
        research_state['progress'] = 100
        research_state['is_researching'] = False
        
        self.memory.add_finding(session_id, "Researcher", findings, sources)
        self.chat_manager.add_chat(topic, 'single', 0, research_state['results'], sources)
        
        return result
   
    def conduct_research_counsel(self, topic: str, num_members: int = 2) -> List[Dict]:
        """Single research pass + parallel counsel analysis + voting"""
        global research_state
        
        research_state['is_researching'] = True
        research_state['progress'] = 0
        research_state['results'] = []
        research_state['sources'] = []
        research_state['votes'] = []
        
        # Phase 1: Deep Research (single pass)
        research_state['current_agent'] = '🔍 Conducting Deep Research...'
        research_state['progress'] = 10
        
        user_context = self.memory.get_user_context()
        
        print(f"\n{'='*70}")
        print(f" RESEARCH TOPIC: {topic}")
        print(f" COUNSEL MEMBERS: {num_members}")
        print(f"{'='*70}")
        
        print(f"\n{'='*70}")
        print(f"PHASE 1: DEEP RESEARCH")
        print(f"{'='*70}")
        
        research_data, sources = self.research_engine.conduct_deep_research(topic, self.model)
        
        print(f"\n RESEARCH SUMMARY:")
        print(f"Total sources gathered: {len(sources)}")
        print(f"Research content length: {len(research_data)} characters")
        print(f"First 1000 chars of research data:\n{research_data[:1000]}...")
        
        research_state['sources'] = sources
        research_state['progress'] = 40
        
        # Add research summary to results
        research_result = {
            'agent': ' Research Findings',
            'content': research_data,
            'sources': sources,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'isResearch': True
        }
        research_state['results'].append(research_result)
        
        # Phase 2: Parallel Counsel Analysis
        print(f"\n{'='*70}")
        print(f"PHASE 2: COUNSEL ANALYSIS")
        print(f"{'='*70}")
        
        perspectives = [
            ("Analyst Alpha", "critical analysis and skepticism"),
            ("Analyst Beta", "practical applications and real-world implications"),
            ("Analyst Gamma", "historical context and long-term trends"),
            ("Analyst Delta", "ethical considerations and societal impact"),
            ("Analyst Epsilon", "technical depth and scientific accuracy"),
            ("Analyst Zeta", "creative connections and alternative viewpoints")
        ]
        
        counsel_members = [
            CounselMember(perspectives[i % len(perspectives)][0], 
                         perspectives[i % len(perspectives)][1],
                         self.model, 
                         self.ollama)
            for i in range(num_members)
        ]
        
        agent_names = [m.name for m in counsel_members]
        session_id = self.memory.add_research_session(topic, agent_names)
        
        research_state['current_agent'] = f'👥 {num_members} Counsel Members Analyzing...'
        
        print(f"\n Providing research data to all {num_members} counsel members...")
        print(f" Research data being shared:\n{research_data[:500]}...\n")
        
        # Parallel analysis
        def analyze_member(member):
            return member.analyze(topic, research_data, sources)
        
        counsel_analyses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_members) as executor:
            future_to_member = {executor.submit(analyze_member, member): member for member in counsel_members}
            
            completed = 0
            for future in concurrent.futures.as_completed(future_to_member):
                member = future_to_member[future]
                try:
                    analysis = future.result()
                    completed += 1
                    
                    progress_contribution = (50 / num_members) * completed
                    research_state['progress'] = int(40 + progress_contribution)
                    
                    result = {
                        'agent': f' {member.name}',
                        'perspective': member.perspective,
                        'content': analysis,
                        'sources': [],
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'isCounsel': True
                    }
                    
                    research_state['results'].append(result)
                    counsel_analyses.append({'member': member.name, 'analysis': analysis})
                    self.memory.add_finding(session_id, member.name, analysis, [])
                    
                except Exception as e:
                    print(f"⚠ Error with {member.name}: {e}")
        
        # Phase 3: Voting
        print(f"\n{'='*70}")
        print(f"PHASE 3: COUNSEL VOTING")
        print(f"{'='*70}")
        
        research_state['current_agent'] = '️ Counsel Members Voting...'
        research_state['progress'] = 92
        
        votes = self._conduct_voting(agent_names)
        research_state['votes'] = votes
        
        # Display voting results
        print(f"\n️ VOTING RESULTS:")
        for vote in votes:
            print(f"  {vote['voter']} voted for: {vote['voted_for']}")
        
        vote_counts = {}
        for vote in votes:
            voted_for = vote['voted_for']
            vote_counts[voted_for] = vote_counts.get(voted_for, 0) + 1
        
        winner = max(vote_counts, key=vote_counts.get)
        print(f"\n🏆 WINNER: {winner} with {vote_counts[winner]} votes!")
        
        # Add voting result to results
        voting_summary = f"**COUNSEL VOTING RESULTS**\n\n"
        for agent in agent_names:
            count = vote_counts.get(agent, 0)
            voting_summary += f"{agent}: {'🔵' * count} ({count} votes)\n"
        voting_summary += f"\n🏆 **Winner: {winner}** with {vote_counts[winner]} votes!"
        
        voting_result = {
            'agent': '️ Voting Results',
            'content': voting_summary,
            'sources': [],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'isVoting': True,
            'votes': votes
        }
        research_state['results'].append(voting_result)
        
        # Phase 4: Final Synthesis
        print(f"\n{'='*70}")
        print(f"PHASE 4: FINAL SYNTHESIS")
        print(f"{'='*70}")
        
        research_state['current_agent'] = ' Generating Final Synthesis...'
        research_state['progress'] = 95
        
        all_analyses = "\n\n".join([f"{r['agent']}: {r['content']}" for r in research_state['results'] if r.get('isCounsel')])
        
        print(f"\n Synthesis input:")
        print(f"Research data length: {len(research_data)} chars")
        print(f"All analyses length: {len(all_analyses)} chars")
        
        synthesis_prompt = f"""Topic: {topic}

Research Findings:
{research_data[:1500]}

Counsel Member Analyses:
{all_analyses[:2000]}

Voting Results: {winner} won with {vote_counts[winner]} votes out of {num_members} total votes.

Provide a comprehensive synthesis that:
1. Summarizes key findings
2. Highlights areas of agreement/disagreement among counsel members (aka Analysts)
3. Draws final conclusions
4. Notes confidence level
5. Acknowledges the winning analysis from {winner}

IMPORTANT RULES - FOLLOW STRICTLY:
- Base ENTIRE synthesis ONLY on the provided research findings and counsel analyses.
- Stay strictly on-topic: Discuss ONLY the {topic}. Do NOT introduce unrelated topics, examples, or diversions.
- Create a cohesive, integrated final report tying everything together.
- Make sure you're relying not just on one source but look through all of the research. (example: dont just rely on the wikipedia results)
- Be concise: 4-6 paragraphs.
- No hallucinations: Do not add new information."""

        synthesis_system = "You are a synthesis expert. Create clear, integrated final report following all rules exactly."
        
        synthesis = self.ollama.generate(
            self.model,
            synthesis_prompt,
            synthesis_system
        )
        
        synthesis_result = {
            'agent': ' Final Synthesis',
            'content': synthesis,
            'sources': [],
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'isSynthesis': True
        }
        
        research_state['results'].append(synthesis_result)
        research_state['progress'] = 100
        research_state['is_researching'] = False
        
        print(f"\n{'='*70}")
        print(f"✓ RESEARCH COMPLETE")
        print(f"{'='*70}\n")
        
        self.chat_manager.add_chat(topic, 'counsel', num_members, research_state['results'], sources, votes)
        
        return research_state['results']
    
    def _conduct_voting(self, agent_names: List[str]) -> List[Dict]:
        """Conduct random voting among counsel members (PewDiePie style)"""
        votes = []
        
        for voter in agent_names:
            # Each member votes for someone else (not themselves)
            possible_votes = [name for name in agent_names if name != voter]
            voted_for = random.choice(possible_votes)
            
            votes.append({
                'voter': voter,
                'voted_for': voted_for,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            })
        
        return votes

# Flask routes
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/models', methods=['GET'])
def get_models():
    ollama = OllamaClient()
    models = ollama.list_models()
    return jsonify({'models': models})

@app.route('/api/memory', methods=['GET'])
def get_memory():
    """Get memory data"""
    memory = MemoryManager()
    return jsonify(memory.memory)

@app.route('/api/chats', methods=['GET'])
def get_chats():
    """Get chats data"""
    chat_manager = ChatManager()
    return jsonify({'chats': chat_manager.chats})

@app.route('/api/research', methods=['POST'])
def start_research():
    data = request.json
    topic = data.get('topic')
    model = data.get('model')
    mode = data.get('mode', 'single')
    num_members = data.get('num_members', 2)
   
    if not topic or not model:
        return jsonify({'error': 'Missing topic or model'}), 400
   
    ollama = OllamaClient()
    memory = MemoryManager()
    chat_manager = ChatManager()
    counsel = ResearchCounsel(model, ollama, memory, chat_manager)
   
    def run_research():
        if mode == 'single':
            counsel.conduct_research_single(topic)
        else:
            counsel.conduct_research_counsel(topic, num_members)
   
    thread = threading.Thread(target=run_research)
    thread.start()
   
    return jsonify({'status': 'started'})

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(research_state)

if __name__ == "__main__":
    print("=" * 70)
    print("--------------------------------------------")
    print("LIMERITA DEEP RESEARCH - AI COUNSEL SYSTEM..")
    print("=" * 70)
    print("\n Starting server...")
    print(" Open browser: http://localhost:5000")
    print(" #!WARNING!Ensure Ollama is running @: localhost:11434")
    print(" #Single-pass research with parallel counsel analysis!")
    print(" #Memory-enabled AI system")
    print("--------------------------------------------")
    print("\n" + "=" * 70 + "\n")
   
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)