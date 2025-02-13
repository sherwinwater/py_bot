import json
import asyncio
import nodriver as uc
import os
from datetime import datetime
import random

# Determine the directory and file path
__dirname = os.path.dirname(os.path.abspath(__file__))
file_name = os.path.join(__dirname, "monster_ca_job_listings.json")

# Utility: Append data to a JSON file
async def append_to_file(filename, data):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        existing_data = []
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as file:
                existing_data = json.load(file)
        existing_data.extend(data)
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=2)
    except Exception as e:
        print("Error writing to file:", e)

# Utility: Randomized delay
async def delay(min_ms, max_ms=8000):
    random_time = random.randint(min_ms, max_ms) / 1000
    print(f"Delaying for {random_time} seconds")
    await asyncio.sleep(random_time)

async def prepare_child_missions(browser, mission_limit=1):
    base_url = "https://www.monster.ca/jobs"
    page = await browser.get(base_url)
    print(f"Navigated to {base_url}")
    try:
        # Delay to ensure the page loads completely
        await delay(2000, 4000)

        # Extract job titles using CSS selectors
        job_title_selector = "div.browse-jobs-list__list ul.item-list--browse-jobs--job-titles li a"
        print(f"Checking job_title_selector: {job_title_selector}")
        job_title_elements = await page.select_all(job_title_selector)

        print(f"Found {len(job_title_elements)} job title elements.")

        missions = []
        for job_title_elem in job_title_elements:
            job_title_href = "https://www.monster.ca" + job_title_elem["href"]
            if not job_title_href:
                continue

            # Open the job title link in a new tab
            new_tab = await browser.get(job_title_href, new_tab=True)
            await delay(2000, 4000)

            # Extract sub-job titles
            sub_job_title_selector = "div.browse-jobs-list__list ul li a"
            sub_job_title_elements = await new_tab.select_all(sub_job_title_selector)
            print(f"Found {len(sub_job_title_elements)} sub job title elements in {job_title_href}")

            for sub_elem in sub_job_title_elements:
                sub_href = sub_elem["href"]
                sub_text = sub_elem.text
                if sub_href:
                    mission = {
                        "initial_link_location": sub_text.strip(),
                        "startUrl": sub_href
                    }
                    missions.append(mission)
                if mission_limit and len(missions) >= mission_limit:
                    break
            await new_tab.close()
            if mission_limit and len(missions) >= mission_limit:
                break
        print(f"Prepared {len(missions)} child missions.")
        return missions
    except Exception as error:
        print('Error during prepare_child_missions:', error)
        return []


async def process_child_mission(browser, mission):
    print(f"Processing mission: {mission['startUrl']}")
    page = await browser.get(mission["startUrl"])
    try:
        await delay(3000, 5000)

        # Scroll and load job listings
        no_more_results_selector = 'button[data-testid="svx-no-more-results-disabled-button"]'
        max_scrolls = 50
        has_no_more_results_button = False

        for i in range(max_scrolls):
            no_more_button = await page.select(no_more_results_selector)
            if no_more_button:
                print("Reached the end of the listings (No More Results button found).")
                has_no_more_results_button = True
                break

            await page.evaluate('window.scrollBy(0, window.innerHeight);')
            await delay(2000, 4000)
            print(f"Scrolled {i + 1} times.")

        if not has_no_more_results_button:
            print("Warning: 'No More Results' button not found within max scroll attempts. Continuing with whatever data is loaded...")

        # Extract job listings
        job_card_selector = '[data-testid="JobCard"]'
        job_cards = await page.select_all(job_card_selector)
        print(f"Found {len(job_cards)} job listings.")

        job_listings = []
        for card in job_cards:
            title_elem = await card.query_selector('[data-testid="jobTitle"]')
            company_elem = await card.query_selector('[data-testid="company"]')
            location_elem = await card.query_selector('[data-testid="jobDetailLocation"]')
            posted_time_elem = await card.query_selector('[data-testid="jobDetailDateRecency"]')
            job_url =  "https:"+title_elem["href"] if title_elem else None

            job = {
                "title": title_elem.text if title_elem else '',
                "company": company_elem.text if company_elem else '',
                "location": location_elem.text if location_elem else '',
                "postedTime": posted_time_elem.text if posted_time_elem else '',
                "jobUrl": job_url or '',
                "scrapedAt": datetime.utcnow().isoformat(),
                "source": mission["initial_link_location"]
            }

            if job["jobUrl"]:
                detail_page = await browser.get(job["jobUrl"], new_tab=True)
                try:
                    await delay(3000, 4000)
                    # job["detailContent"] = await detail_page.get_content()
                    job["detailContent"] = "done"
                except Exception as err:
                    print(f"Error fetching details for {job['jobUrl']}: {err}")
                    job["detailContent"] = None
                finally:
                    await detail_page.close()

            job_listings.append(job)

        print(f"Mission {mission['startUrl']}: Collected {len(job_listings)} job listings with details.")
        return job_listings
    except Exception as error:
        print(f"Error processing mission {mission['startUrl']}: {error}")
        return []


async def main():
    # Configure mission limit; default to 5 if not set in environment variables.
    mission_limit = int(os.getenv('CHILD_MISSION_LIMIT', 5))

    # Start the browser session
    browser = await uc.start(
        headless=False,
        browser_args=["--window-size=920,980"]
    )

    print(f"Browser started. {browser}")

    try:
        # PREPARE: Get child missions using the specified workflow and selectors.
        missions = await prepare_child_missions(browser, mission_limit)
        print(f"Prepared {len(missions)} child missions.")

        # PAYLOAD: Process each child mission sequentially.
        for mission in missions:
            mission_result = await process_child_mission(browser, mission)
            await append_to_file(file_name, mission_result)  # Append data after each mission.
            print(f"Appended results of mission to {file_name}")

        print(f"Completed processing all missions. Data saved to {file_name}")
    except Exception as error:
        print('Error during main execution:', error)
    finally:
        browser.stop()

if __name__ == "__main__":
    asyncio.run(main())
