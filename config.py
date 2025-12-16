import os
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_MODEL = "mistral-large-latest"

TARGET_PRODUCT = "n8n"
COMPETITORS = ["Zapier", "Make", "Integromat", "Microsoft Power Automate", "IFTTT"]

SAMPLE_QUERIES = [
    "What automation tools are suitable for startups and small businesses?",
    "Comparison of Zapier vs Make for workflow automation",
    "How to automate lead generation for small businesses?",
    "Review of no-code automation platforms in 2025",
    "Which tool is best for CRM and email marketing integration?",
    "Automation tools for connecting different business applications",
    "How to set up automation without coding skills?",
    "Price comparison of popular automation platforms",
    "Best Zapier alternatives for startups on a budget",
    "Integration of Slack, Trello, and Gmail through automation tools",
    "n8n review and use cases for developers",
    "Make.com vs Integromat - which is better for complex workflows?",
    "Microsoft Power Automate pros and cons for enterprise use",
    "Open source automation tools comparison",
    "How to choose the right automation platform for your business needs?",
    "Workflow automation tools with free tier options",
    "API integration platforms for non-technical users",
    "Self-hosted automation solutions review",
    "Best automation tools for e-commerce businesses",
    "Comparing cloud-based vs on-premise automation platforms"
]

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "market_analysis.log"

MISTRAL_RATE_LIMIT = 30

AUTO_UPDATE_ENABLED = True
UPDATE_SCHEDULE_HOUR = 12
UPDATE_QUERIES_COUNT = 15

DAILY_QUERIES = [
    f"What's new with {TARGET_PRODUCT} today?",
    f"Latest updates about {TARGET_PRODUCT} in 2025",
    f"Recent reviews of {TARGET_PRODUCT} vs competitors",
    f"How has {TARGET_PRODUCT} improved recently?",
    f"Current market position of {TARGET_PRODUCT}",
    f"{TARGET_PRODUCT} recent features and updates",
    f"User feedback about {TARGET_PRODUCT} this month",
    f"Comparison: {TARGET_PRODUCT} vs {COMPETITORS[0]} in 2025",
    f"Is {TARGET_PRODUCT} still a good choice for startups?",
    f"Recent integrations added to {TARGET_PRODUCT}",
    f"Pricing changes for {TARGET_PRODUCT} recently",
    f"New use cases for {TARGET_PRODUCT} in 2025",
    f"Community feedback about {TARGET_PRODUCT}",
    f"Technical improvements in {TARGET_PRODUCT}",
    f"Market trends for automation tools including {TARGET_PRODUCT}"
]