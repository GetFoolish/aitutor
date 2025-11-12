
Always use: /Users/vandanchopra/Vandan_Personal_Folder/CODE_STUFF/Projects/venvs/aitutor/bin/python to run
lets look at the file for our To-dos and wrap then up one by one. Keep making the human test each task manually and getting an OK from them before you mark it [DONE] and decide to move on.

------ TO DO ------
[DONE] 1. Start with the left console minimized (the one which has the gemini audio and video status updates.)
[DONE] 2. In the main console display a dummy khan academy question that i can solve. a simple addition sum should suffice.
[DONE] 3. In the main window, lets have a khan academy style scratchpad that can be opened up if someone presses the pencil icon.
[DONE]4. change the name of left-section to 'question-panel'. and change the name of the media-mixer panel to media-mixer-display. also, lets also make the media-mixer-display collapsable to the right side of the screen.
[DONE] 5. Now lets move the dash_system.py file into a folder of it's own with the name 'DashSystem'.
[DONE] 6. lets move skills.json and curriculum.json to a folder called 'QuestionsBank'. make sure to refactor any files that are using these two files.
[DONE] 7. Lets check if dash_system.py has a function / method that decides which the next question should be. it will be based on Next Skill to be practiced 'recommendation' function, based on 'current skills table'.
8. Now lets add the skill bar / menu.
9. Now develop the frontend like khan academy where we will display the next question. and test it.







------- OTHER STUFF -------
1. Student Learning Path & Proficiency Tracking
    1. ✅ Create a bkt bayesian knowledge tracing system alternative called DASH by Mozer and Lindsay (read file: @dash.md), which has the learning path for Math from K to 12.
    2. ✅ Now write a quick script to check if step 1 is working. Give is a random question from a random module, and let the human input Y/N (Y=student got the question right, N=student got the question wrong) -- Print a table with previous score and new score for all modules that were updated.
    3. ✅ When the system starts, look for the json for for the user ID. If one doesn't exist, create an empty start point. Each user will have their own json file in a folder called 'Users'. Each json file will have: a) current skill table, b) list of questions answered (correctly / wrongly) maintained c) Student Notes (Empty for now)
    4. ✅ Next Skill to be practiced 'recommendation' function, based on 'current skills table'
    5. ✅ In @curriculum.json, every question should also include the 'correct' answer.
    6. ✅ Question Generator Agent: This is an AI generator with an LLM in the background, which will take a question as an input, and then give us a new variation of the question. This variation will get added to the curriculum.json file as needed, so that it can be used in future. 
    7. Curriculum Builder Agent: We need an agent that will go on the internet, and find new questions that we can test the student on. Lets try and make sure that we don't add new questions that are similar to the ones we have in our @curriculum.json file already.
        1. Where can we source content from?


2. Gemini Live API Integration:
    1. lets have a folder called frontend. in that folder, we want to have a page called 'classroom.html'. This page has the following functionality:
        1. It has one main section where you have a khan academy style question, with a khan academy style scratchpad that can be toggled on / off, which overlays on top of the main section.
        4) In addition to this, you also have a @live-api-web-console 




Next Features:
1. Right now curriculum is being saved in 1 file. over time that's not scalable. lets make it one file per skill instead.

1. Google Live API Integration: (Gagan)
    3. Now, integrate Google Live API, so that i talk to it. Here is the documentation url for the same: https://ai.google.dev/gemini-api/docs/live-guide?_gl=1*17cgr2i*_up*MQ..*_ga*MjY3OTU1NDMxLjE3NTA0MzE4NzY.*_ga_P1DBVKWT6V*czE3NTA0MzE4NzYkbzEkZzAkdDE3NTA0MzE4ODckajQ5JGwwJGgxNDY3NDIzMzcz

2. Long Term Memory: (Gagan / Vandan)

3. Making it a good tutor: Like chandler from the movie + https://youtu.be/Vh6A76z1kiM?si=e3MeP9uKmhG955Is

4. Expand the Skills in the Curriculum: https://github.com/AlefEducation/IXL_Scraper/blob/master/SkillScraper.py
