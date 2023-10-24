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
from httpx import ConnectTimeout, HTTPStatusError, TimeoutException

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

    def __init__(self, scrape_job_details: bool = True) -> None:
        super().__init__()
        self.__scrape_job_details = scrape_job_details
        self.__job_listings_limiter = AsyncLimiter(4, 9)
        self.__job_details_limiter = AsyncLimiter(4, 9)
        self.__scrape_jobs_tasks: list[asyncio.Task[list[Job]]] = []
        self.__scrape_details_tasks: list[asyncio.Task[JobDetails | None]] = []

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
                await self.__job_listings_limiter.acquire()
                logger.info(f"getting jobs for {params}")
                response = await self._client.get(
                    url=self.LINKEDIN_SEARCH_URL,
                    params=params,
                    follow_redirects=True,
                    timeout=10,
                )
                response.raise_for_status()
                self.__scrape_jobs_tasks.append(
                    asyncio.create_task(self.parse(response)),
                )
                start += self.RESULTS_PER_PAGE
                retries = 0
            except (HTTPStatusError, ConnectTimeout, TimeoutException):
                msg = f"rate limited while getting jobs for {params}"
                logger.warning(msg)
                retries += 1
                if retries > self.MAX_RETRIES:
                    break
                # synchronized sleep to avoid flooding
                sleep(self.RETRY_DELAY)  # noqa: ASYNC101
            # useful to check for not explicitly handled exceptions
            except Exception as e:
                msg = "not explicitly handled exception occurred; please open an issue"
                logger.error(msg)
                logger.exception(e)
                raise

        for task in self.__scrape_jobs_tasks:
            jobs += await task

        if self.__scrape_job_details:
            for task in self.__scrape_details_tasks:
                await task

        logger.info(f"successfully scraped {len(jobs)} jobs")
        return jobs

    async def parse(self, response: Response) -> list[Job]:
        soup = BeautifulSoup(response.text, "lxml")
        raw_jobs = soup.find_all("div", class_="base-card")
        if not raw_jobs:
            return []
        logger.info(f"gathering {len(raw_jobs)} job parse requests")
        jobs = await asyncio.gather(
            *(self.parse_job(raw_job) for raw_job in raw_jobs),
        )
        logger.info(f"successfully parsed {len(jobs)} jobs")
        return jobs

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
        location_parts = location_section.text.split(",")
        location_parts_len = len(location_parts)
        city = location_parts[0].strip().lower() if location_parts_len >= 1 else None
        if location_parts_len >= 2:
            region = location_parts[1].strip()
            region = region if region.isupper() else region.lower()
        else:
            region = None
        if location_parts_len >= 3:
            country = Country.from_alias(location_parts[2].strip().lower())
        else:
            country = Country.WORLDWIDE
        location = Location(city=city, region=region, country=country)

        job = Job(
            title=title,
            link=link,
            company=company,
            location=location,
        )

        if self.__scrape_job_details:
            self.__scrape_details_tasks.append(
                asyncio.create_task(self.get_job_details(job)),
            )

        return job

    async def get_job_details(self, job: Job) -> JobDetails | None:
        params = {
            "_l": "en_US",
        }
        retries = 0
        job_details = None

        while retries < self.MAX_RETRIES:
            try:
                await self.__job_details_limiter.acquire()
                logger.info(f"getting job details from {job.link}")
                response = await self._client.get(
                    job.link,
                    params=params,
                    follow_redirects=True,
                    timeout=10,
                )
                response.raise_for_status()
                job_details = self.parse_job_details(response)
            except (  # noqa: PERF203
                HTTPStatusError,
                ConnectTimeout,
                TimeoutException,
                LinkedInBadPageError,
            ):
                msg = f"rate limited while getting job details from {job.link}"
                logger.warning(msg)
                retries += 1
                if retries > self.MAX_RETRIES:
                    break
                # synchronized sleep to avoid flooding
                sleep(self.RETRY_DELAY)  # noqa: ASYNC101
            # useful to check for not explicitly handled exceptions
            except Exception as e:
                msg = "not explicitly handled exception occurred; please open an issue"
                logger.error(msg)
                logger.exception(e)
                raise
            else:
                logger.info(f"successfully parsed job details from {job.link}")
                job.details = job_details
                return job_details
        msg = f"can't get job details from {job.link}"
        logger.warning(msg)
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
            "li",
            class_="description__job-criteria-item",
        )

        for criteria_section in criteria_sections:
            criteria_title = criteria_section.h3.get_text(strip=True)
            criteria_value = criteria_section.span.text.strip().lower()
            match criteria_title:
                case "Seniority level":
                    seniority_level = criteria_value.replace("-", "").replace(" ", "")
                case "Employment type":
                    employment_type = EmploymentType.from_alias(
                        criteria_value.replace("-", "").replace(" ", ""),
                    )
                case "Job function":
                    job_function = criteria_value
                case "Industries":
                    industries = criteria_value
                case _:
                    pass

        return JobDetails(
            description=description,
            employment_type=employment_type,
            seniority_level=seniority_level,
            job_function=job_function,
            industries=industries,
        )
