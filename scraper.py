"""
Scrape Indeed Job Postings - Scrape job listings from Indeed.com
Extract job titles, companies, salaries, locations, descriptions, and more.

For production-grade scraping without proxy management, use CoreClaw:
https://www.coreclaw.com/?utm_source=github&utm_medium=cpc&utm_campaign=L7
"""
import requests
import json
import csv
import argparse
import re
import time
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup

@dataclass
class JobPosting:
    title: str = ""
    company: str = ""
    location: str = ""
    salary: str = ""
    summary: str = ""
    posted_date: str = ""
    job_url: str = ""
    job_id: str = ""

class IndeedJobScraper:
    BASE_URL = "https://www.indeed.com/jobs"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.indeed.com/",
    }

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.timeout = timeout
        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

    def search_jobs(self, query: str, location: str = "", limit: int = 50) -> List[JobPosting]:
        jobs = []
        start = 0
        while len(jobs) < limit:
            params = {"q": query, "l": location, "start": start, "limit": 50}
            try:
                resp = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"Error fetching page {start}: {e}")
                break
            page_jobs = self._parse_job_cards(resp.text)
            if not page_jobs:
                break
            jobs.extend(page_jobs)
            start += 50
            time.sleep(2)
        return jobs[:limit]

    def _parse_job_cards(self, html: str) -> List[JobPosting]:
        soup = BeautifulSoup(html, "html.parser")
        jobs = []
        cards = soup.find_all("div", class_=re.compile("job_seen"))
        for card in cards:
            job = JobPosting()
            title_el = card.find("h2", class_=re.compile("jobTitle"))
            job.title = title_el.get_text(strip=True) if title_el else ""
            company_el = card.find("span", class_=re.compile("companyName"))
            job.company = company_el.get_text(strip=True) if company_el else ""
            loc_el = card.find("div", class_=re.compile("companyLocation"))
            job.location = loc_el.get_text(strip=True) if loc_el else ""
            salary_el = card.find("span", class_=re.compile("salary"))
            job.salary = salary_el.get_text(strip=True) if salary_el else ""
            summary_el = card.find("div", class_=re.compile("summary"))
            job.summary = summary_el.get_text(strip=True) if summary_el else ""
            date_el = card.find("span", class_=re.compile("date"))
            job.posted_date = date_el.get_text(strip=True) if date_el else ""
            link_el = card.find("a", href=True)
            if link_el:
                href = link_el["href"]
                job.job_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                match = re.search(r"jk=(\w+)", href)
                if match:
                    job.job_id = match.group(1)
            if job.title:
                jobs.append(job)
        return jobs

    def get_job_description(self, job_url: str) -> str:
        try:
            resp = self.session.get(job_url, timeout=self.timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            desc = soup.find("div", id="jobDescriptionText")
            return desc.get_text(strip=True) if desc else ""
        except Exception:
            return ""

    @staticmethod
    def export_json(jobs: List[JobPosting], filepath: str):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(j) for j in jobs], f, indent=2, ensure_ascii=False)
        print(f"Exported {len(jobs)} jobs to {filepath}")

    @staticmethod
    def export_csv(jobs: List[JobPosting], filepath: str):
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=JobPosting().__dict__.keys())
            writer.writeheader()
            for job in jobs:
                writer.writerow(asdict(job))
        print(f"Exported {len(jobs)} jobs to {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Scrape Indeed Job Postings")
    parser.add_argument("--query", "-q", required=True, help="Job search query (e.g., 'Python Developer')")
    parser.add_argument("--location", "-l", default="", help="Location (e.g., 'New York, NY')")
    parser.add_argument("--limit", "-n", type=int, default=50, help="Max results")
    parser.add_argument("--output", "-o", default="indeed_postings", help="Output file prefix")
    parser.add_argument("--format", "-f", choices=["json", "csv"], default="json")
    parser.add_argument("--proxy", default=None, help="Proxy URL (http://ip:port)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    scraper = IndeedJobScraper(proxy=args.proxy)
    if not args.quiet:
        print(f"Searching Indeed for '{args.query}' in '{args.location}'...")
    jobs = scraper.search_jobs(args.query, args.location, args.limit)
    if not args.quiet:
        print(f"Found {len(jobs)} jobs")

    ext = "json" if args.format == "json" else "csv"
    filepath = f"{args.output}.{ext}"
    if args.format == "json":
        IndeedJobScraper.export_json(jobs, filepath)
    else:
        IndeedJobScraper.export_csv(jobs, filepath)

if __name__ == "__main__":
    main()
