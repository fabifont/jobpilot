from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from loguru import logger

from jobpilot.scrapers import BaseScraper

if TYPE_CHECKING:
    from httpx import Response

    from jobpilot.scrapers import ScraperInput


import asyncio

from aiolimiter import AsyncLimiter
from bs4 import Tag
from httpx import HTTPStatusError

from jobpilot.models import Company, Country, EmploymentType, Job, JobDetails, Location


class LinkedInError(Exception):
    pass


class LinkedInBadPageError(LinkedInError):
    pass


class LinkedInScraper(BaseScraper):
    LINKEDIN_SEARCH_URL = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    )
    LINKEDIN_JOB_URL = "https://www.linkedin.com/jobs/view"
    START_LIMIT = 1000
    MAX_RETRIES = 5
    RETRY_DELAY = 5
    RESULTS_PER_PAGE = 25

    def __init__(self) -> None:
        super().__init__()
        self.__limiter = AsyncLimiter(5, 8)

    async def scrape(self, scraper_input: ScraperInput) -> list[Job]:
        params = {
            "keywords": scraper_input.keywords,
            "location": scraper_input.location,
            "pageNum": 0,
            "_l": "en_US",
        }
        limit = min(scraper_input.limit, self.START_LIMIT)
        start = 0
        retries = 0
        jobs: list[Job] = []

        while start < limit:
            params["start"] = start
            try:
                await self.__limiter.acquire()
                logger.info(f"getting jobs for {params}")
                response = await self._client.get(
                    url=self.LINKEDIN_SEARCH_URL,
                    params=params,
                    follow_redirects=True,
                )
                response.raise_for_status()

                new_jobs = await self.parse(response)
                if not new_jobs:
                    break
                logger.info(f"successfully parsed {len(new_jobs)} jobs")
                jobs += new_jobs

                start += self.RESULTS_PER_PAGE
                retries = 0
            except HTTPStatusError as e:
                if e.response.status_code == 429:
                    self._waiting = True
                    retries += 1
                    if retries > self.MAX_RETRIES:
                        break

                    wait_time = int(
                        e.response.headers.get("Retry-After", self.RETRY_DELAY),
                    )
                    # synchronized sleep to avoid flooding
                    sleep(wait_time)  # noqa: ASYNC101
                else:
                    msg = (
                        "not explicitly handled HTTP exception occurred; please open an"
                        " issue"
                    )
                    logger.error(msg)
                    raise
            # useful to check for not explicitly handled exceptions
            except Exception:
                msg = "not explicitly handled exception occurred; please open an issue"
                logger.error(msg)
                raise
        logger.info(f"successfully scraped {len(jobs)} jobs")
        return jobs

    async def parse(self, response: Response) -> list[Job]:
        soup = BeautifulSoup(response.text, "lxml")
        raw_jobs = soup.find_all("div", class_="base-card")
        if not raw_jobs:
            return []
        logger.info(f"gathering {len(raw_jobs)} job parse requests")
        return await asyncio.gather(
            *(self.parse_job(raw_job) for raw_job in raw_jobs),
        )

    async def parse_job(self, raw_job: Tag) -> Job:
        title_section = raw_job.find("a", class_="base-card__full-link")
        if not title_section or not title_section.has_attr("href"):  # type: ignore
            msg = "Job title or link not found"
            raise LinkedInError(msg)
        title = title_section.text.strip().lower()
        # clean link
        job_id: str = title_section["href"].split("?")[0].split("-")[-1]  # type: ignore
        link = f"{self.LINKEDIN_JOB_URL}/{job_id}"

        company_section = raw_job.find("h4", class_="base-search-card__subtitle").find(
            "a",
            class_="hidden-nested-link",  # type: ignore
        )
        if not company_section or not company_section.has_attr("href"):  # type: ignore
            msg = "Company name or link not found"
            raise LinkedInError(msg)
        company_name = company_section.text.strip().lower()
        company_link: str = company_section["href"]  # type: ignore
        company = Company(name=company_name, link=company_link)

        location_section = raw_job.find("span", class_="job-search-card__location")
        location_str = location_section.text.split(",")
        if len(location_str) < 3:
            city, region = location_str
            country = Country.WORLDWIDE
        else:
            city, region, country_str = location_str
            country = Country.from_alias(country_str.strip().lower())
        city = city.strip().lower()
        region = region if region.isupper() else region.strip().lower()
        location = Location(city=city, region=region, country=country)

        details = await self.get_job_details(link)

        return Job(
            title=title,
            link=link,
            company=company,
            location=location,
            details=details,
        )

    async def get_job_details(self, link: str) -> JobDetails | None:
        params = {
            "_l": "en_US",
        }
        retries = 0
        job_details = None

        while retries < self.MAX_RETRIES:
            try:
                await self.__limiter.acquire()
                logger.info(f"getting job details from {link}")
                response = await self._client.get(
                    link,
                    params=params,
                    follow_redirects=True,
                )
                response.raise_for_status()
                job_details = self.parse_job_details(response)
            except HTTPStatusError as e:  # noqa: PERF203
                if e.response.status_code == 429 or e.response.status_code == 500:
                    retries += 1
                    if retries > self.MAX_RETRIES:
                        msg = "Too many retries"
                        raise LinkedInError(msg) from e

                    wait_time = int(
                        e.response.headers.get("Retry-After", self.RETRY_DELAY),
                    )
                    # synchronized sleep to avoid flooding
                    sleep(wait_time)  # noqa: ASYNC101
                else:
                    msg = (
                        "not explicitly handled HTTP exception occurred; please open an"
                        " issue"
                    )
                    logger.error(msg)
                    raise
            except LinkedInBadPageError:
                sleep(self.RETRY_DELAY)  # noqa: ASYNC101
            # useful to check for not explicitly handled exceptions
            except Exception:
                msg = "not explicitly handled exception occurred; please open an issue"
                logger.error(msg)
                raise
            else:
                logger.info(f"successfully parsed job details from {link}")
                return job_details
        msg = "couldn't get job details"
        logger.error(msg)
        return job_details

    def parse_job_details(self, response: Response) -> JobDetails:
        soup = BeautifulSoup(response.text, "lxml")

        description: str | None = None
        employment_type: EmploymentType | None = None
        seniority_level: str | None = None
        job_function: str | None = None
        industries: str | None = None

        description_section = soup.find(
            "div",
            class_="show-more-less-html__markup",
        )
        if description_section is None:
            msg = "Job description section not found"
            raise LinkedInBadPageError(msg)
        if isinstance(description_section, Tag):
            description = description_section.text.strip()

        criteria_sections = soup.find_all(
            "span",
            class_="description__job-criteria-text",
        )
        seniority_level = (
            criteria_sections[0].text.replace("-", "").replace(" ", "").strip().lower()
        )
        employment_type = EmploymentType.from_alias(
            criteria_sections[1].text.replace("-", "").replace(" ", "").strip().lower(),
        )
        job_function = criteria_sections[2].text.strip().lower()
        industries = criteria_sections[3].text.strip().lower()

        return JobDetails(
            description=description,
            employment_type=employment_type,
            seniority_level=seniority_level,
            job_function=job_function,
            industries=industries,
        )
