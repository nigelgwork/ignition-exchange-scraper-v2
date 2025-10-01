"""
Comparison logic for detecting new and updated resources
"""
import re
from typing import List, Dict, Tuple
from datetime import datetime


def extract_resource_id(url: str) -> int:
    """Extract resource ID from URL"""
    match = re.search(r'/exchange/(\d+)/', url)
    if match:
        return int(match.group(1))
    return 999999  # Default for URLs without ID


def compare_resources(current_results: List[Dict], past_results: List[Dict]) -> List[Dict]:
    """
    Compare current scrape results with past results to identify new or updated resources.

    A resource is considered updated if:
    - It has a new Resource ID (not in past results)
    - The version has changed for an existing Resource ID
    - The updated_date has changed for an existing Resource ID

    Args:
        current_results: List of resources from current scrape
        past_results: List of resources from previous scrape

    Returns:
        List of resources that are either new or updated
    """
    # Create lookup dict for past results by Resource ID
    past_lookup = {}
    for resource in past_results:
        url = resource.get('url', '')
        resource_id = extract_resource_id(url)
        past_lookup[resource_id] = resource

    updated_resources = []

    for current in current_results:
        url = current.get('url', '')
        resource_id = extract_resource_id(url)

        if resource_id not in past_lookup:
            # New resource - Resource ID not in past results
            updated_resources.append(current)
        else:
            # Check if updated - compare version and date
            past = past_lookup[resource_id]

            # Compare version and updated_date
            current_version = current.get('version', '')
            past_version = past.get('version', '')

            current_date = current.get('updated_date', '')
            past_date = past.get('updated_date', '')

            # Consider it updated if version or date differs
            if current_version != past_version or current_date != past_date:
                updated_resources.append(current)

    return updated_resources


def get_comparison_stats(current_results: List[Dict], past_results: List[Dict],
                         updated_results: List[Dict]) -> Dict:
    """
    Get statistics about the comparison

    Returns:
        Dict with statistics
    """
    # Build sets of Resource IDs
    past_ids = {extract_resource_id(r.get('url', '')) for r in past_results}
    current_ids = {extract_resource_id(r.get('url', '')) for r in current_results}
    updated_ids = {extract_resource_id(r.get('url', '')) for r in updated_results}

    new_ids = current_ids - past_ids
    removed_ids = past_ids - current_ids

    # Count truly new vs updated
    new_count = len(new_ids & updated_ids)  # New IDs that are in updated list
    updated_count = len(updated_results) - new_count  # Modified existing resources

    return {
        'total_current': len(current_results),
        'total_past': len(past_results),
        'total_updated': len(updated_results),
        'new_count': new_count,
        'modified_count': updated_count,
        'removed_count': len(removed_ids),
        'new_ids': sorted(list(new_ids)),
        'removed_ids': sorted(list(removed_ids))
    }
