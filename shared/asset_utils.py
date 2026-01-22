import re
from typing import Any, Dict, List

def convert_graphie_url(url: str) -> str:
    """
    Convert Perseus graphie URLs to standard HTTPS URLs or local overrides.
    """
    if not url or not isinstance(url, str):
        return url

    # Handle web+graphie:// protocol
    if url.startswith('web+graphie://'):
        # FIXED: Specific override for Question 6933689e1a5cae918f8bec3a (Hint 3)
        if 'e66544a9df611c00a03c44091f17ab1be4c19f1a' in url:
             return '/assets/graphie-fix-6933689-hint3.svg'

        # MAXWELL-BOLTZMANN GRAPH FIXES
        maxwell_mapping = {
            # Set 1 (ID 6936dfa7 and others)
            '9d20d5d50558725c38cf44c88220105f251911a6': '/fixed_graphs/maxwell_main.png',
            '52a083afb7e78f5ef019b0c473e1bd37036907e3': '/fixed_graphs/maxwell_cooled.png',
            'df617a190927b3d2882c60184d173e0ba94e2014': '/fixed_graphs/maxwell_heated.png',
            '8502c7e500b06f69e3135e03cd12f8c741042dee': '/fixed_graphs/maxwell_choice_2.png',
            '0497f4001d2c449dcbb860162bbd54de4a1749d0': '/fixed_graphs/maxwell_choice_3.png',
            '71b9f63cc34d600a8da4778474d4cf81bb2ec56f': '/fixed_graphs/maxwell_cooled.png',
            # Set 2
            '52674a647f4d1b8b0313bbda7ec4cc706f3d6bfd': '/fixed_graphs/maxwell_main.png',
            'f0824638c844a983430e6112691fdd758155b0da': '/fixed_graphs/maxwell_cooled.png',
            'ec8110af073c2e7458e9a3f8298e236a4721fc76': '/fixed_graphs/maxwell_heated.png',
            '11f3e2ea39e8ffb45ff60fc29b6b14a6e4e79f05': '/fixed_graphs/maxwell_choice_2.png',
            'da99687350361a06ddb07e694f677689c1952fe2': '/fixed_graphs/maxwell_choice_3.png',
            # Set 0 (Legacy fixed in DB but potentially inconsistent/low quality)
            '1dfc8bfcc0a8e9ce5516355ed0e281a70b27dc79': '/fixed_graphs/maxwell_main.png',
            '472a35f297edf7fb059cb8225fbb98f51699c1ff': '/fixed_graphs/maxwell_cooled.png',
            'dc7187375c0d4942e951132d2913425c0611006f': '/fixed_graphs/maxwell_heated.png',
            'e3e5a87d7bdf70d26e9c8cefbc34bd4ab55e8fac': '/fixed_graphs/maxwell_choice_2.png',
            'fc38b3c732b8a2222348835e7685105bbe11ccce': '/fixed_graphs/maxwell_choice_3.png',
            # Legacy Filenames found in DB
            'question_69305a56_main.png': '/fixed_graphs/maxwell_main.png',
            'question_69305a56_choice_0.png': '/fixed_graphs/maxwell_cooled.png',
            'question_69305a56_choice_1.png': '/fixed_graphs/maxwell_heated.png',
            'question_69305a56_choice_2.png': '/fixed_graphs/maxwell_choice_2.png',
            'question_69305a56_choice_3.png': '/fixed_graphs/maxwell_choice_3.png',
        }

        for h, local_path in maxwell_mapping.items():
            if h in url:
                return local_path

        # Remove protocol and add https
        clean_url = url.replace('web+graphie://', 'https://')

        # Add .svg extension if not present
        if not clean_url.endswith(('.svg', '.png', '.jpg', '.jpeg', '.gif')):
            clean_url += '.svg'

        return clean_url

    return url

def fix_all_urls_in_string(text: str) -> str:
    """
    Find and replace all web+graphie:// URLs in a string using convert_graphie_url mapping.
    """
    if not text or not isinstance(text, str):
        return text
    
    # Pattern to find web+graphie:// URLs
    urls = re.findall(r'web\+graphie://[^\s)\]\"\'<>]+', text)
    
    # Also handle some legacy fixed URLs
    legacy_patterns = [
        'question_69305a56_main.png',
        'question_69305a56_choice_0.png',
        'question_69305a56_choice_1.png',
        'question_69305a56_choice_2.png',
        'question_69305a56_choice_3.png'
    ]
    
    # Process found URLs
    for url in set(urls):
        fixed_url = convert_graphie_url(url)
        if fixed_url != url:
            text = text.replace(url, fixed_url)
            
    # Process legacy patterns
    for pattern in legacy_patterns:
        if pattern in text:
            fixed = convert_graphie_url(pattern)
            if fixed != pattern:
                text = text.replace(pattern, fixed)
                
    return text

def apply_recursive_asset_fix(target: Any) -> None:
    """
    Recursively find and convert web+graphie:// URLs in a dictionary or list.
    """
    if isinstance(target, dict):
        for k, v in target.items():
            if isinstance(v, str):
                # Check for common image fields or just any string that might have a URL
                target[k] = fix_all_urls_in_string(v)
            else:
                apply_recursive_asset_fix(v)
    elif isinstance(target, list):
        for i, item in enumerate(target):
            if isinstance(item, str):
                target[i] = fix_all_urls_in_string(item)
            else:
                apply_recursive_asset_fix(item)
