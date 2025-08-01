import asyncio
import os
import json
import csv
import re
from datetime import datetime
from playwright.async_api import Page, BrowserContext, TimeoutError
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
)
from fastmcp.exceptions import ToolError

# --- Configuration (loaded from environment) ---
FILE_MANAGEMENT_TEMP_DIR = os.getenv('FILE_MANAGEMENT_TEMP_DIR', '/tmp/sentient_files')
LINKEDIN_COOKIES_PATH = os.getenv('LINKEDIN_COOKIES_PATH')

# --- Constants ---
PLATFORM_NAME = "LinkedIn"
SCREENSHOT_DIR = "debug_screenshots_linkedin" # This will be inside the user's temp dir
FEED_URL = "https://www.linkedin.com/feed/"

# --- Helper & Hook Functions (from user script) ---
async def _load_and_normalize_cookies(context: BrowserContext, cookies_path: str, platform_name: str) -> bool:
    if not cookies_path or not os.path.exists(cookies_path):
        raise ToolError(f"System configuration error: LinkedIn cookies file not found. Please contact the administrator.")
    
    print(f"[{platform_name} Session] Found cookies file at: {cookies_path}. Loading cookies...")
    try:
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
            cookies = cookies_data.get('cookies', cookies_data) if isinstance(cookies_data, dict) else cookies_data

        normalized_cookies = []
        for cookie in cookies:
            samesite_val = cookie.get('sameSite')
            if samesite_val is None or str(samesite_val).lower() not in ['strict', 'lax', 'none']:
                cookie['sameSite'] = 'Lax'
            else:
                samesite_lower = str(samesite_val).lower()
                if samesite_lower == 'strict': cookie['sameSite'] = 'Strict'
                elif samesite_lower == 'lax': cookie['sameSite'] = 'Lax'
                elif samesite_lower in ['none', 'no_restriction']: cookie['sameSite'] = 'None'
            normalized_cookies.append(cookie)
        
        await context.add_cookies(normalized_cookies)
        print(f"[{platform_name} Session] Successfully loaded and normalized {len(normalized_cookies)} cookies.")
        return True
    except Exception as e:
        raise ToolError(f"Failed to load/add cookies from file: {e}")

async def manage_linkedin_session(page: Page, context: BrowserContext, **kwargs) -> bool:
    cookies_path = kwargs.get("cookies_path")
    if not cookies_path:
        raise ToolError("Cookies path not provided to session manager.")

    print(f"[{PLATFORM_NAME} Session] Verifying login status...")
    await _load_and_normalize_cookies(context, cookies_path, PLATFORM_NAME)

    current_cookies = await context.cookies()
    if any(c.get('name') == 'li_at' and '.linkedin.com' in c.get('domain', '') for c in current_cookies):
        print(f"[{PLATFORM_NAME} Session] Valid 'li_at' cookie found. Login is active.")
        return True
    
    raise ToolError("No valid 'li_at' cookie found in the system's cookie file. The session may have expired. Please contact the administrator.")

# --- Automator Class (adapted from user script) ---
class LinkedInAutomator:
    def __init__(self, page: Page, context: BrowserContext, session_id: str, output_dir: str):
        self.page = page
        self.context = context
        self.session_id = session_id
        self.service_name = "linkedin"
        self.jobs_data = []
        self.processed_job_ids = set()
        self.output_dir = output_dir
        self.screenshot_dir = os.path.join(output_dir, SCREENSHOT_DIR)
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.screenshot_counter = 0

    async def _take_screenshot(self, name: str):
        if self.page and not self.page.is_closed():
            self.screenshot_counter += 1
            safe_name = re.sub(r'[\\/*?:"<>|]', "", name)
            path = os.path.join(self.screenshot_dir, f"{self.session_id}-{self.screenshot_counter:02d}-{safe_name}.png")
            try:
                await self.page.screenshot(path=path)
                print(f"[{self.service_name}] Screenshot saved: {path}")
            except Exception as e:
                print(f"[{self.service_name}] Failed to save screenshot {path}: {e}")

    async def run(self, search_query: str, num_jobs: int) -> str:
        print(f"[{self.service_name}] Starting LinkedIn job scraping for '{search_query}' ({num_jobs} jobs).")
        try:
            # Step 1: Navigate to feed (already done by crawler) and search
            await self._perform_search(search_query)

            # Step 2: Scrape results
            await self._scrape_job_listings(num_jobs)

        except Exception as e:
            await self._take_screenshot("critical-error")
            raise ToolError(f"A critical error occurred during the run: {e}")
        finally:
            print(f"[{self.service_name}] Automation finished. Collected {len(self.jobs_data)} jobs.")
            if self.jobs_data:
                return await self._save_to_csv()
            return "No jobs were found or scraped."

    async def _perform_search(self, search_query: str):
        print(f"[{self.service_name}] Performing job search for: '{search_query}'")
        try:
            await self.page.wait_for_selector('a[href*="/jobs/"]', state="visible", timeout=30000)
            await self._take_screenshot("feed-loaded")
            
            await self.page.click('a[href*="/jobs/"]')
            
            semantic_input_selector = 'input[aria-label="Search by title, skill, or company"]'
            await self.page.wait_for_selector(semantic_input_selector, state="visible", timeout=30000)
            await self._take_screenshot("jobs-page-loaded")

            await self.page.fill(semantic_input_selector, search_query)
            await self._take_screenshot("search-form-filled")

            await self.page.press(semantic_input_selector, "Enter")
            print(f"[{self.service_name}] Search submitted.")

        except Exception as e:
            await self._take_screenshot("search-step-failed")
            raise ToolError(f"Failed during the initial search steps: {e}")

    async def _scrape_job_listings(self, num_jobs: int):
        job_list_selector = "ul.semantic-search-results-list"
        await self.page.wait_for_selector(job_list_selector, state="visible", timeout=60000)
        await self._take_screenshot("job-results-loaded")

        while len(self.jobs_data) < num_jobs:
            job_cards = await self.page.locator("div.job-card-job-posting-card-wrapper[data-job-id]").all()
            if not job_cards:
                print(f"[{self.service_name}] No job cards found on the page. Exiting.")
                break
            
            new_jobs_found_in_this_pass = False
            for card in job_cards:
                if len(self.jobs_data) >= num_jobs: break
                job_id = await card.get_attribute("data-job-id")
                if job_id in self.processed_job_ids: continue
                
                new_jobs_found_in_this_pass = True
                self.processed_job_ids.add(job_id)

                try:
                    await card.scroll_into_view_if_needed()
                    title = await card.locator(".artdeco-entity-lockup__title").inner_text()
                    company = await card.locator(".artdeco-entity-lockup__subtitle").inner_text()
                    location = await card.locator(".artdeco-entity-lockup__caption").inner_text()
                    job_url = await card.locator("a.job-card-job-posting-card-wrapper__card-link").get_attribute("href")
                    
                    await card.click()
                    
                    description_selector = "div#job-details"
                    await self.page.wait_for_selector(description_selector, state="visible", timeout=15000)
                    await asyncio.sleep(1.5)
                    
                    description = await self.page.locator(description_selector).inner_text()

                    self.jobs_data.append({
                        "job_id": job_id, "title": title.strip(), "company": company.strip(),
                        "location": location.strip(), "description": description.strip(), "url": job_url
                    })
                    print(f"[{self.service_name}] Scraped job {len(self.jobs_data)}/{num_jobs}: {title.strip()}")
                except (TimeoutError, Exception) as e:
                    print(f"[{self.service_name}] Could not process job card {job_id}. Error: {e}")
                    await self._take_screenshot(f"error-job-{job_id}")
                    continue
            
            if len(self.jobs_data) >= num_jobs: break

            if new_jobs_found_in_this_pass:
                scroll_panel_selector = "ul.semantic-search-results-list"
                await self.page.evaluate(f'document.querySelector("{scroll_panel_selector}").scrollTop += 600')
                await asyncio.sleep(2)
            else:
                try:
                    next_button_locator = self.page.locator('button[aria-label="View next page"]')
                    if await next_button_locator.is_visible():
                        await next_button_locator.click()
                        await asyncio.sleep(3)
                    else:
                        print(f"[{self.service_name}] No 'Next' page button found. Ending search.")
                        break
                except Exception:
                    print(f"[{self.service_name}] Reached end of job listings.")
                    break

    async def _save_to_csv(self) -> str:
        if not self.jobs_data:
            return "No job data was collected to save."

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"linkedin_jobs_{timestamp}.csv"
        output_filepath = os.path.join(self.output_dir, output_filename)
        
        csv_columns = ["job_id", "title", "company", "location", "url", "description"]
        
        try:
            with open(output_filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
                writer.writeheader()
                writer.writerows(self.jobs_data)
            print(f"[{self.service_name}] Successfully saved {len(self.jobs_data)} jobs to '{output_filepath}'")
            # Return the relative path for the agent
            return os.path.relpath(output_filepath, FILE_MANAGEMENT_TEMP_DIR)
        except IOError as e:
            raise ToolError(f"Error saving data to CSV file: {e}")

# --- Main Entry Point for MCP ---
async def perform_job_search(user_id: str, search_query: str, num_jobs: int) -> str:
    if not LINKEDIN_COOKIES_PATH:
        raise ToolError("System configuration error: LINKEDIN_COOKIES_PATH is not set.")

    user_output_dir = os.path.join(FILE_MANAGEMENT_TEMP_DIR, user_id)
    os.makedirs(user_output_dir, exist_ok=True)

    browser_config = BrowserConfig(
        headless=True,
        use_persistent_context=False,
        user_data_dir=None,
        use_managed_browser=False,
        viewport={"width": 1920, "height": 1080}
    )
    
    session_id = f"linkedin_scraper_{int(asyncio.get_event_loop().time())}"
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        crawler.crawler_strategy.set_hook(
            "on_page_context_created", 
            lambda page, context, **kwargs: manage_linkedin_session(page, context, cookies_path=LINKEDIN_COOKIES_PATH, **kwargs)
        )
        
        run_config = CrawlerRunConfig(
            session_id=session_id,
            page_timeout=90000,
            cache_mode=CacheMode.BYPASS,
            magic=True
        )
        
        result = await crawler.arun(url=FEED_URL, config=run_config)
        
        if not result.success:
            raise ToolError("Failed to load LinkedIn initial page. Check cookies or network.")

        page, context = await crawler.crawler_strategy.browser_manager.get_page(run_config)
        automator = LinkedInAutomator(page, context, session_id, user_output_dir)

        try:
            login_button_selector = 'button.member-profile__details'
            await page.wait_for_selector(login_button_selector, state="visible", timeout=10000)
            await page.click(login_button_selector)
        except TimeoutError:
            pass # Already on feed

        return await automator.run(search_query, num_jobs)