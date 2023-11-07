import asyncio
import json
import tempfile
from pathlib import Path

import jobpilot
from jobpilot.scrapers import LinkedInScraper, ScraperInput

jobpilot.enable_logging()

scraper = LinkedInScraper()
scraper_input = ScraperInput(
    location="italy",
    keywords="software engineer",
    limit=50,
)

jobs = asyncio.run(scraper.scrape(scraper_input, job_details=True))

temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
path = Path(temp_file.name)

with path.open("w") as f:
    json.dump([job.model_dump() for job in jobs], f, indent=4, default=str)

print(f"Jobs saved to {path}")  # noqa: T201
