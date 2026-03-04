"""
Tavily API client for web search functionality.
Provides intelligent web search optimized for AI/LLM applications.
"""
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class TavilyClient:
    """Client for Tavily Search API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"

    def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer: bool = True,
    ) -> dict[str, Any]:
        """Perform web search using Tavily API"""
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": search_depth,
                "max_results": min(max_results, 10),
                "include_answer": include_answer,
            }

            logger.info("🔍 Tavily search: %s", query)

            response = requests.post(
                f"{self.base_url}/search",
                json=payload,
                timeout=30,
            )

            response.raise_for_status()
            result = response.json()

            logger.info("✅ Tavily returned %d results", len(result.get("results", [])))

            return result

        except Exception:
            logger.exception("❌ Tavily API error")
            return {"error": "Tavily API error", "results": [], "answer": None}

    def format_results_for_llm(
        self, search_result: dict[str, Any], filter_location: Optional[str] = None
    ) -> str:
        """Format Tavily results for LLM context, optionally filtering by location"""
        if "error" in search_result:
            return f"⚠️ Search error: {search_result['error']}"

        parts: list[str] = []

        # Add AI answer
        if search_result.get("answer"):
            answer = search_result["answer"]
            # If filtering by location, only include answer if it mentions the location
            if filter_location:
                location_variations = [
                    filter_location.lower(),
                    filter_location.lower().replace(" ", ""),  # "losangeles"
                    filter_location.split()[0].lower() if " " in filter_location else None,
                ]
                location_variations = [v for v in location_variations if v]

                if any(loc in answer.lower() for loc in location_variations):
                    parts.append(f"📊 ANSWER FOR {filter_location.upper()}:\n{answer}\n")
                else:
                    logger.info("⚠️ Filtering out answer - doesn't mention %s", filter_location)
            else:
                parts.append(f"📊 ANSWER:\n{answer}\n")

        # Add search results
        results = search_result.get("results", [])
        if results:
            filtered_count = 0
            temp_results: list[str] = []

            for idx, result in enumerate(results, 1):
                title = result.get("title", "No title")
                url = result.get("url", "")
                content = result.get("content", "")

                # If filtering by location, only include results that mention the location
                if filter_location:
                    combined_text = f"{title} {content}".lower()
                    location_variations = [
                        filter_location.lower(),
                        filter_location.lower().replace(" ", ""),
                        " la " if "los angeles" in filter_location.lower() else None,
                    ]
                    location_variations = [v for v in location_variations if v]

                    # Check if this result is about the target location
                    if any(loc in combined_text for loc in location_variations):
                        temp_results.append(
                            f"\n{filtered_count + 1}. {title}\n"
                            f"   URL: {url}\n"
                            f"   {content[:300]}...\n"
                        )
                        filtered_count += 1
                        logger.info("✅ Kept result %d: %s (mentions %s)", idx, title, filter_location)
                    else:
                        logger.info("❌ Filtered out result %d: %s (doesn't mention %s)", idx, title, filter_location)
                else:
                    temp_results.append(
                        f"\n{idx}. {title}\n"
                        f"   URL: {url}\n"
                        f"   {content[:300]}...\n"
                    )

            if temp_results:
                parts.append(f"🔍 WEB SEARCH RESULTS FOR {filter_location.upper() if filter_location else 'QUERY'}:\n")
                parts.extend(temp_results)
            elif filter_location:
                parts.append(f"\n⚠️ No web results specifically about {filter_location} were found.\n")
                logger.warning("⚠️ Location filter removed all %d results for '%s'", len(results), filter_location)

        result_text = "\n".join(parts)
        logger.info("📄 Formatted results: %d chars, %s", len(result_text), filter_location or "no filter")
        return result_text
