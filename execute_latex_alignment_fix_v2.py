import os
import json
import re
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv('.env')
client = MongoClient(os.getenv('MONGODB_URI'), serverSelectionTimeoutMS=120000, connectTimeoutMS=120000)
db = client[os.getenv('MONGODB_DB_NAME') or 'ai_tutor']

# Shortened list of IDs (from the 222 found)
# I will fetch them dynamically again but with a simpler query if possible
# or just target the one question first and then the rest.
# Actually, the timeout happened during the regex search. 
# A search by ID list is MUCH faster.

target_ids = [
    "692fad867e334152c5f47410", "692fad907e334152c5f47412", "692fad9e7e334152c5f47414",
    "692fada47e334152c5f47415", "692fada87e334152c5f47416", "69300587b70fca208973fd1f",
    "69300592b70fca208973fd21", "6930059eb70fca208973fd23", "693005a3b70fca208973fd24",
    "693005abb70fca208973fd25", "69303959ef2f010d12847ae0", "69303964ef2f010d12847ae2",
    "6930396def2f010d12847ae4", "69303971ef2f010d12847ae5", "69303977ef2f010d12847ae6",
    "69306fc373cb28d3e4ce41d8", "69306fd073cb28d3e4ce41da", "69306fdc73cb28d3e4ce41dc",
    "69306fe273cb28d3e4ce41dd", "69306fe673cb28d3e4ce41de", "6930a82f5c0a695d8e36a2af",
    "6930a8355c0a695d8e36a2b0", "6930a8525c0a695d8e36a2b5", "6930df4971fa8d5e7b610724",
    "6930df5271fa8d5e7b610726", "6930df5e71fa8d5e7b610728", "6930df6171fa8d5e7b610729",
    "6930df6571fa8d5e7b61072a", "69310f10321b4d5e799b3b3c", "69310f18321b4d5e799b3b3e",
    "69310f23321b4d5e799b3b40", "69310f28321b4d5e799b3b41", "69310f2b321b4d5e799b3b42",
    "69315799bd78eec1e54b51ef", "693157a6bd78eec1e54b51f1", "693157b1bd78eec1e54b51f3",
    "693157b7bd78eec1e54b51f4", "693157bdbd78eec1e54b51f5", "693180df47a2cb48fc68c33a",
    "693180e647a2cb48fc68c33b", "6931810247a2cb48fc68c340", "6931d07236979a821f00f13f",
    "6931d07d36979a821f00f141", "6931d08836979a821f00f143", "6931d08f36979a821f00f144",
    "6931d09536979a821f00f145", "6931ef09efcbea09d0af76e6", "6931ef15efcbea09d0af76e8",
    "6931ef20efcbea09d0af76ea", "6931ef26efcbea09d0af76eb", "6931ef2defcbea09d0af76ec",
    "693243d4440e2b61d583a158", "693243e0440e2b61d583a15a", "693243e9440e2b61d583a15c",
    "693243f0440e2b61d583a15d", "693243f7440e2b61d583a15e", "69325f06611a50e452585f95",
    "69325f0f611a50e452585f97", "69325f1a611a50e452585f99", "69325f21611a50e452585f9a",
    "69325f26611a50e452585f9b", "6932b1d8cf05997b77546d0d", "6932b1decf05997b77546d0e",
    "6932b1f8cf05997b77546d13", "6932cce35853fec4a559722f", "6932ccee5853fec4a5597231",
    "6932ccfa5853fec4a5597233", "6932cd005853fec4a5597234", "6932cd065853fec4a5597235",
    "693327a30630c0293933e9d6", "693327a80630c0293933e9d7", "693327c20630c0293933e9dc",
    "693327c70630c0293933e9dd", "693366001a5cae918f8bebee", "693366041a5cae918f8bebef",
    "6933661e1a5cae918f8bebf4", "693397ff20538a6f3167f7da", "6933980820538a6f3167f7dc",
    "6933981420538a6f3167f7de", "6933981b20538a6f3167f7df", "6933982020538a6f3167f7e0",
    "6933d72945a4cb2e2ed444e0", "6933d73345a4cb2e2ed444e2", "6933d73f45a4cb2e2ed444e4",
    "6933d74645a4cb2e2ed444e5", "6933d74d45a4cb2e2ed444e6", "69340ebd948fc265153f4502",
    "69342bc194c7597a1c30b620", "69342bc894c7597a1c30b621", "6934476b4736cfd74285fa4a",
    "693447744736cfd74285fa4c", "693447814736cfd74285fa4e", "693447844736cfd74285fa4f",
    "6934478a4736cfd74285fa50", "69348008e9d6a82e390ae42f", "6934800fe9d6a82e390ae430",
    "69348026e9d6a82e390ae435", "6934b7e16a69d82b28838e19", "6934b7e56a69d82b28838e1a",
    "6934b7fe6a69d82b28838e1f", "6934e2805ce616487e704cf4", "6934e2875ce616487e704cf5",
    "6934e2925ce616487e704cf7", "6934e2965ce616487e704cf8", "6934e29a5ce616487e704cf9",
    "6934e29e5ce616487e704cfa", "6934e2a25ce616487e704cfb", "6934e2aa5ce616487e704cfd",
    "6934f128cd4923e2c34531f8", "6934f131cd4923e2c34531fa", "6934f13ccd4923e2c34531fc",
    "6934f141cd4923e2c34531fd", "6934f148cd4923e2c34531fe", "69352a284c2368e642b768c4",
    "69352a2c4c2368e642b768c5", "69352a4a4c2368e642b768ca", "6935630f70be2a4e56f9f331",
    "69359c0e7eb357b3c8738578", "69359c197eb357b3c873857a", "69359c267eb357b3c873857c",
    "69359c2a7eb357b3c873857d", "69359c2f7eb357b3c873857e", "6935d3df7f7bb4dc34f4d340",
    "6935d3e87f7bb4dc34f4d342", "6935d3f47f7bb4dc34f4d344", "6935d3f87f7bb4dc34f4d345",
    "6935d3fd7f7bb4dc34f4d346", "69360d3f0aabe66864660c4e", "69360d450aabe66864660c4f",
    "69360d5d0aabe66864660c54", "693646b903d86cedf65fa6d8", "693646c603d86cedf65fa6da",
    "693646d203d86cedf65fa6dc", "693646d703d86cedf65fa6dd", "693646db03d86cedf65fa6de",
    "69367fdbbe093d84ab4ec631", "69367fe7be093d84ab4ec633", "69367ff2be093d84ab4ec635",
    "69367ff9be093d84ab4ec636", "69368000be093d84ab4ec637", "6936b92134f949d0ebe6fbe7",
    "6936b92b34f949d0ebe6fbe9", "6936b93934f949d0ebe6fbeb", "6936b93f34f949d0ebe6fbec",
    "6936b94534f949d0ebe6fbed", "6936f82eb753254d0bf6fe5d", "693730dcd416931ff461b9b3",
    "693947665cee42ae00ae8a87", "6939476b5cee42ae00ae8a88", "693947725cee42ae00ae8a89",
    "693947775cee42ae00ae8a8a", "693948495cee42ae00ae8a90", "693948505cee42ae00ae8a91",
    "693948595cee42ae00ae8a92", "6939485d5cee42ae00ae8a93", "693948625cee42ae00ae8a94",
    "69394a025cee42ae00ae8aa0", "69394a075cee42ae00ae8aa1", "69394a0d5cee42ae00ae8aa2",
    "69394a125cee42ae00ae8aa3", "69394a1a5cee42ae00ae8aa4", "69394a285cee42ae00ae8aa6",
    "69394a2e5cee42ae00ae8aa7", "69394a365cee42ae00ae8aa8", "69394b005cee42ae00ae8aae",
    "69394b055cee42ae00ae8aaf", "69394b0d5cee42ae00ae8ab0", "69394b135cee42ae00ae8ab1",
    "69394b1b5cee42ae00ae8ab2", "69394cb75cee42ae00ae8abe", "69394cbd5cee42ae00ae8abf",
    "69394cc85cee42ae00ae8ac1", "693969622737c15fd599bf1a", "69396fad70ea40fca0c8d1ec",
    "69396fb970ea40fca0c8d1ee", "69396fc170ea40fca0c8d1ef", "69396fcb70ea40fca0c8d1f1",
    "69396fd470ea40fca0c8d1f3", "69396fdc70ea40fca0c8d1f4", "693972ab70ea40fca0c8d20a",
    "693972b970ea40fca0c8d20c", "693972bf70ea40fca0c8d20d", "69397f2393ffc72ddaed8fb1",
    "69397f2993ffc72ddaed8fb2", "69397f3193ffc72ddaed8fb3", "69397f3693ffc72ddaed8fb4",
    "69397f3b93ffc72ddaed8fb5", "69397f4393ffc72ddaed8fb6", "69397f4993ffc72ddaed8fb7",
    "69397f4e93ffc72ddaed8fb8", "69397f5393ffc72ddaed8fb9", "69397f5893ffc72ddaed8fba",
    "6939907cda09f7a0714df806", "69399080da09f7a0714df807", "69399085da09f7a0714df808",
    "6939908bda09f7a0714df809", "69399090da09f7a0714df80a", "69399094da09f7a0714df80b",
    "6939909bda09f7a0714df80c", "693990a0da09f7a0714df80d", "693990a7da09f7a0714df80e",
    "693990adda09f7a0714df80f", "693991a9da09f7a0714df814", "693991bcda09f7a0714df817",
    "693991c3da09f7a0714df818", "693991cada09f7a0714df819", "693994f5da09f7a0714df82e",
    "69399511da09f7a0714df833", "69399517da09f7a0714df834", "69399c80ffbc8575650ea66e",
    "69399c87ffbc8575650ea66f", "69399c8fffbc8575650ea670", "6939c76e30035330ee097026",
    "6939c77430035330ee097027", "6939c89030035330ee09702b", "6939c89730035330ee09702c",
    "6939c89e30035330ee09702d", "6939c9ce30035330ee097033", "6939c9d530035330ee097034",
    "6939c9d930035330ee097035", "6939c9e130035330ee097036", "6939c9e930035330ee097037"
]

def fix_latex(text):
    if not isinstance(text, str):
        return text
    
    # 1. Start tag: align -> array{r}
    text = text.replace(r"\begin{align}", r"\begin{array}{r}")
    # 2. End tag
    text = text.replace(r"\end{align}", r"\end{array}")
    
    # 3. Correct spacing and alignment operators for vertical additions
    # Replace '& \\' or '&  \\' with ' \\' since array{r} already handles the right alignment
    text = re.sub(r"&\s*\\\\", r" \\\\", text)
    
    # 4. Handle multiple backslashes (Perseus often uses \\\\ for newline in JSON)
    # The fix should be robust for both escaped and non-escaped
    
    return text

def recursive_fix(obj):
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k == 'itemData' and isinstance(v, str):
                try:
                    inner_data = json.loads(v)
                    fixed_inner = recursive_fix(inner_data)
                    new_obj[k] = json.dumps(fixed_inner, ensure_ascii=False)
                except:
                    new_obj[k] = fix_latex(v)
            elif isinstance(v, str):
                new_obj[k] = fix_latex(v)
            else:
                new_obj[k] = recursive_fix(v)
        return new_obj
    elif isinstance(obj, list):
        return [recursive_fix(i) for i in obj]
    else:
        return obj

COLLECTION_NAME = 'scraped_questions'
collection = db[COLLECTION_NAME]

print(f"Applying LaTeX fix to {len(target_ids)} questions via ID list...")

updated_count = 0
for q_id in target_ids:
    item = collection.find_one({"_id": ObjectId(q_id)}) or collection.find_one({"_id": q_id})
    if item:
        fixed_item = recursive_fix(item)
        collection.replace_one({"_id": item["_id"]}, fixed_item)
        updated_count += 1
        if updated_count % 50 == 0:
            print(f"  Processed {updated_count} questions...")
    else:
        print(f"  Warning: Question {q_id} not found.")

print(f"Finished. Total updated: {updated_count}")
