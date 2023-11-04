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


class LinkedInNoMoreJobsError(LinkedInError):
    def __init__(self, message: str = "no more jobs") -> None:
        super().__init__(message)


class LinkedInTooManyRetriesError(LinkedInError):
    def __init__(self, message: str = "too many retries") -> None:
        super().__init__(message)


class LinkedInScraper(BaseScraper):
    LINKEDIN_SEARCH_URL = (
        "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    )
    LINKEDIN_JOB_URL = "https://www.linkedin.com/jobs/view"
    # linkedin APIs accepts maximum 1000 as start parameter with 25 results per page
    START_LIMIT = 1000
    RESULTS_PER_PAGE = 25
    MAX_RETRIES = 5
    RETRY_DELAY = 5

    def __init__(self) -> None:
        super().__init__()
        self.__limiter = AsyncLimiter(5, 8)
        self.__lock = asyncio.Lock()
        self.__last_start_with_results = -self.START_LIMIT

    async def scrape(
        self,
        scraper_input: ScraperInput,
        job_details: bool = False,
    ) -> list[Job]:
        # minimum between input limit and start limit
        limit = min(scraper_input.limit, self.START_LIMIT)

        # start all tasks to get job listings
        tasks = [
            asyncio.create_task(
                self.get_jobs(scraper_input.keywords, scraper_input.location, start),
            )
            for start in range(0, limit, self.RESULTS_PER_PAGE)
        ]

        # wait till first exception
        # this is useful because linkedin will return 200 even if there are no more jobs
        # so a LinkedInNoMoreJobsError is raised
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        # cancel pending tasks to avoid useless requests
        for task in pending:
            task.cancel()

        jobs: list[Job] = []

        # get results from done tasks
        for task in done:
            task_exception = task.exception()
            # raise exception if not a LinkedInNoMoreJobsError
            # otherwise add scraped jobs to list
            if task_exception:
                if not isinstance(task_exception, LinkedInNoMoreJobsError):
                    raise task_exception
            else:
                jobs += task.result()

        # fill job details if requested
        if job_details:
            await self.fill_jobs_details(jobs)

        return jobs

    async def get_jobs(self, keywords: str, location: str, start: int) -> list[Job]:
        params = {
            "keywords": keywords,
            "location": location,
            "pageNum": 0,
            "_l": "en_US",
            "start": start,
        }
        retries = 0

        while retries < self.MAX_RETRIES:
            try:
                # wait for a free slot in the limiter
                await self.__limiter.acquire()

                logger.info(f"getting jobs for {params}")

                response = await self._client.get(
                    url=self.LINKEDIN_SEARCH_URL,
                    params=params,
                    follow_redirects=True,
                    timeout=10,
                )
                response.raise_for_status()

                jobs = self.parse_jobs(response)
            except (HTTPStatusError, ConnectTimeout, TimeoutException):  # noqa: PERF203
                msg = f"rate limited while getting jobs for {params}"
                logger.warning(msg)

                # synchronized sleep to avoid flooding
                sleep(self.RETRY_DELAY)  # noqa: ASYNC101
                retries += 1
            except Exception as e:
                msg = "not explicitly handled exception occurred; please open an issue"
                logger.error(msg)
                logger.exception(e)
                raise
            else:
                logger.info(f"successfully scraped {len(jobs)} jobs")

                # check if there are no more jobs
                async with self.__lock:
                    if jobs:
                        if start > self.__last_start_with_results:
                            self.__last_start_with_results = start
                    else:
                        if (
                            start
                            == self.__last_start_with_results + self.RESULTS_PER_PAGE
                        ):
                            raise LinkedInNoMoreJobsError
                return jobs
        raise LinkedInTooManyRetriesError

    def parse_jobs(self, response: Response) -> list[Job]:
        soup = BeautifulSoup(response.text, "lxml")
        raw_jobs = soup.find_all("div", class_="base-card")

        return [self.parse_job(raw_job) for raw_job in raw_jobs]

    def parse_job(self, raw_job: Tag) -> Job:
        title_section = raw_job.find("a", class_="base-card__full-link")

        if not title_section or not title_section.has_attr("href"):  # type: ignore
            msg = "Job title or link not found"
            raise LinkedInError(msg)

        title = title_section.text.strip().lower()

        # remove useless stuff from link to create a clean link
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

        city = None
        region = None
        country = Country.WORLDWIDE
        location_section = raw_job.find("span", class_="job-search-card__location")
        location_parts = location_section.text.split(",")
        location_parts_len = len(location_parts)

        if location_parts_len >= 1:
            location_parts[0].strip().lower()
        if location_parts_len >= 2:
            region = location_parts[1].strip()
            region = region if region.isupper() else region.lower()
        if location_parts_len >= 3:
            country = Country.from_alias(location_parts[2].strip().lower())

        location = Location(city=city, region=region, country=country)

        return Job(
            title=title,
            link=link,
            company=company,
            location=location,
        )

    async def fill_jobs_details(self, jobs: list[Job]) -> list[Job]:
        await asyncio.gather(
            *[self.get_job_details(job) for job in jobs],
        )

        return jobs

    async def get_job_details(self, job: Job) -> JobDetails:
        params = {
            "_l": "en_US",
        }
        retries = 0

        while retries < self.MAX_RETRIES:
            try:
                # wait for a free slot in the limiter
                await self.__limiter.acquire()

                logger.info(f"getting job details from {job.link}")

                response = await self._client.get(
                    job.link,
                    params=params,
                    follow_redirects=True,
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

                # synchronized sleep to avoid flooding
                sleep(self.RETRY_DELAY)  # noqa: ASYNC101
                retries += 1
            except Exception as e:
                msg = "not explicitly handled exception occurred; please open an issue"
                logger.error(msg)
                logger.exception(e)
                raise
            else:
                logger.info(f"successfully scraped job details from {job.link}")

                job.details = job_details
                return job_details
        raise LinkedInTooManyRetriesError

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

        # when description is not found is because the page is not loaded correctly
        # this is another rate limit error
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
