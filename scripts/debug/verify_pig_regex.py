
import re

def verify_pig_regex():
    # Simulate the regex used in the components
    # Using the same list as in ImageWidget (which is more comprehensive)
    skipKeywordsRegex = r"\b(beaver|castor|samurai|photograph|photo|forest|star|sky|night|banana|fruit|apple|orange|pear|grape|strawberry|rabbit|bunny|lapin|dog|cat|bird|fish|animal|nature|landscape|pig)s?\b"
    
    alt_text = "A group of seven pigs."
    
    match = re.search(skipKeywordsRegex, alt_text, re.IGNORECASE)
    if match:
        print(f"MATCH SUCCESS: '{alt_text}' matches keyword '{match.group(0)}'")
    else:
        print(f"MATCH FAILED: '{alt_text}' did not match.")

    alt_text_single = "A little pink pig."
    match_single = re.search(skipKeywordsRegex, alt_text_single, re.IGNORECASE)
    if match_single:
         print(f"MATCH SUCCESS: '{alt_text_single}' matches keyword '{match_single.group(0)}'")

if __name__ == "__main__":
    verify_pig_regex()
