from w3lib.html import replace_tags
from scrapy.item import Item, Field
from scrapy.loader import ItemLoader
from scrapy.loader.processors import Identity
from scrapy.loader.processors import MapCompose
from scrapylib.processors import default_input_processor, default_output_processor
from brightcorp.processors import NormalizedJoin

class BrightcorpItem(Item):

    # system parameter
    mining_job_id = Field()
    site_id = Field()
    batch_id = Field()
    iteration = Field()

    # required fields
    title = Field()
    date = Field()
    expiration_date = Field()
    referencenumber = Field()
    url = Field()
    company = Field()
    company_description = Field()
    location = Field()
    zip_code = Field()
    description = Field()
    jobcategory = Field()
    jobtype = Field()
    org_name = Field()
    apply_url = Field()

    # optional fields
    industry = Field()
    duration = Field()
    baseSalary = Field()
    benefits = Field()
    educationrequirements = Field()
    experiencerequirements = Field()
    incentives = Field()
    qualifications = Field()
    responsibilities = Field()
    requirements = Field()
    salaryCurrency = Field()
    skills = Field()
    specialcommitments = Field()
    workhours = Field()
    tracking_pixel_url = Field()

    ingested_industry_codes = Field() # the data should be a json array of numbers (the integer mapping can be found here: https://developer.linkedin.com/docs/reference/industry-codes [use the "Code" values])
    functions = Field() # the data should be a json array of strings (enums that can be found here: https://developer.linkedin.com/docs/reference/job-function-codes [use capitalized "Targeting Code" values])
    experience_level = Field() # the data should be a string ("NOT_APPLICABLE", "INTERNSHIP", "ENTRY_LEVEL", "ASSOCIATE", "MID_SENIOR_LEVEL", "DIRECTOR", "EXECUTIVE")

    other = Field()

    iteration = Field()
    spidername = Field()
    start_url = Field()
    on_demand = Field()

    logo_url = Field()

    autoextracted_logo_urls = Field()
    autoextracted_emails = Field()
    autoextracted_salaries = Field()
    autoextracted_company_websites = Field()

    encoding_scrapy_guess = Field()
    encoding_headers = Field()
    encoding_body_declared = Field()
    encoding_body_inferred = Field()

    incremental_crawler_hash = Field()

    # Autocrawler
    raw_html = Field()
    config = Field()
    page_classification = Field()

    language = Field()

    referer = Field()

class BrightcorpItemLoader(ItemLoader):
    default_item_class = BrightcorpItem
    default_input_processor = default_input_processor
    default_output_processor = default_output_processor
    raw_html_in = Identity()
    description_in = Identity()
    description_out = NormalizedJoin()
    experiencerequirements_in = Identity()
    experiencerequirements_out = NormalizedJoin()
    qualifications_in = Identity()
    qualifications_out = NormalizedJoin()
    requirements_in = Identity()
    requirements_out = NormalizedJoin()
    skills_in = Identity()
    skills_out = NormalizedJoin()
    responsibilities_in = Identity()
    responsibilities_out = NormalizedJoin()
    company_description_in = Identity()
    company_description_out = NormalizedJoin()
    benefits_in = Identity()
    benefits_out = NormalizedJoin()
    summary_out = NormalizedJoin()

def replace_tags_with_space(x):
    return replace_tags(x, ' ')

class AutocrawlItemLoader(BrightcorpItemLoader):
    location_in = MapCompose(replace_tags_with_space, default_input_processor)
    location_out = NormalizedJoin()
