import json
import asyncio
import nodriver
import datetime
import os

async def append_to_file(filename, data):
    try:
        existing_data = []
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as file:
                existing_data = json.load(file)

        existing_data.extend(data)
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=2)
    except Exception as e:
        print("Error writing to file:", e)

async def scrape_jobs():
    print("Starting scraper...")

    browser = await nodriver.start(
        chrome_args=[
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
            "--no-first-run",
            "--no-zygote",
            "--headless=false",
            "--enable-logging --v=1"
        ],
        no_sandbox=True,
        chromium_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    )

    page = await browser.get("https://grabjobs.co/canada/jobs-in-canada")

    # Wait for the first job card to appear
    # await page.wait_for_element("a.link-card")
    # Additional small delay if needed
    await asyncio.sleep(20)

    url = "https://grabjobs.co/canada/jobs-in-canada"
    country = url.split("/")[3]
    filename = f"{country}_job_listings.json"

    while True:
        try:
            elems = await page.select_all("a.link-card")
            if not elems:
                print("No job listings found on page")
                break

            jobListings = []
            for elem in elems:
                title = await elem.select("h2")
                company = await elem.select("h3")
                location_elem = await elem.select('img[alt="geo-alt icon"]')
                job_type_elem = await elem.select('img[alt="briefcase icon"]')
                description = await elem.select(".break-words")
                job_url = await elem.get_attr("href")
                posted_time = await elem.select(".text-sm:last-child")

                jobListings.append({
                    "title":       await title.text() if title else "",
                    "company":     await company.text() if company else "",
                    "location":    await location_elem.text() if location_elem else "",
                    "jobType":     await job_type_elem.text() if job_type_elem else "",
                    "description": await description.text() if description else "",
                    "jobUrl":      job_url or "",
                    "postedTime":  await posted_time.text() if posted_time else "",
                    "scrapedAt":   datetime.datetime.utcnow().isoformat()
                })

            await append_to_file(filename, jobListings)
            print(f"Saved {len(jobListings)} jobs")

            next_button = await page.select("a.rounded-e-md:not(.text-gray-400)")
            if next_button:
                await next_button.click()
                # Wait again for next page’s content
                await asyncio.sleep(5)
            else:
                break
        except Exception as e:
            print("Error during scraping:", e)
            break

    await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_jobs())