"""Demo sample resumes + a demo JD. Used by the seed script and tests."""
DEMO_JD = """Senior Backend Engineer (Python / FastAPI)

We are looking for a Senior Backend Engineer to design and scale our AI platform.

Responsibilities:
- Design and build REST APIs using FastAPI and Python
- Work with PostgreSQL and Redis for data storage and caching
- Deploy services with Docker and Kubernetes on AWS
- Integrate LLM-based features (embeddings, semantic search) into the product
- Collaborate with the frontend team building the React dashboard

Requirements:
- 4+ years of professional backend experience with Python
- Strong experience with FastAPI or Django, and REST API design
- Solid SQL skills; PostgreSQL preferred
- Experience with Docker and cloud platforms (AWS preferred)
- Familiarity with machine learning or LLM pipelines is a plus

Nice to have:
- Kubernetes, Terraform
- Experience with vector databases such as FAISS or ChromaDB
"""

SAMPLE_RESUMES = {
    "priya_sharma.txt": """Priya Sharma
Senior Backend Engineer

Email: priya.sharma@example.com | Phone: +91 98765 43210

SUMMARY
Backend engineer with 6 years of experience building scalable Python services and REST APIs.

EXPERIENCE
Senior Software Engineer at InfoEdge | Jan 2021 - Present
- Designed REST APIs with FastAPI serving 2M requests/day, improved p95 latency by 35%
- Built data pipelines with PostgreSQL and Redis caching
- Mentored a team of 3 junior engineers

Software Engineer at TCS | Mar 2018 - Dec 2020
- Developed Django services and integrated MySQL databases
- Automated deployments with Docker and GitHub Actions, reducing release time by 40%

SKILLS
Python, FastAPI, Django, REST API, PostgreSQL, MySQL, Redis, Docker, AWS, Git, Linux

PROJECTS
Realtime Analytics API
- FastAPI + Websockets service streaming metrics to a React dashboard
ML Resume Ranker
- Semantic resume matching with embeddings and FAISS

EDUCATION
B.Tech in Computer Science, IIT Delhi, 2017

CERTIFICATIONS
AWS Certified Solutions Architect – Associate

ACHIEVEMENTS
Improved query performance by 60% through indexing and query optimization
""",
    "arjun_verma.txt": """Arjun Verma
Full Stack Developer

arjun.verma@example.com
+91 90123 45678

SUMMARY
Full stack developer with 3 years of experience building web apps with React and Node.js.

EXPERIENCE
Full Stack Developer at Zomato | Jun 2022 - Present
- Built React dashboards consumed by 100k monthly users
- Developed Node.js REST APIs with MongoDB

Junior Developer at StartupHub | Jul 2021 - May 2022
- Built HTML/CSS/JavaScript landing pages and internal tools

SKILLS
JavaScript, TypeScript, React, Node.js, Express, MongoDB, HTML, CSS, Tailwind CSS, Git

PROJECTS
E-commerce Storefront
- React + Redux storefront with Stripe checkout

EDUCATION
B.Sc in Computer Science, Delhi University, 2021

LANGUAGES
English, Hindi
""",
    "meera_iyer.txt": """Meera Iyer
Machine Learning Engineer

Email: meera.iyer@example.com
Phone: +91 99887 76655

SUMMARY
ML engineer with 5 years of experience in NLP, LLM pipelines and production ML systems.

EXPERIENCE
Senior ML Engineer at Freshworks | Feb 2021 - Present
- Built semantic search with embeddings and ChromaDB, improving recall by 45%
- Deployed model services with Docker and Kubernetes on GCP
- Built NLP pipelines for ticket classification using scikit-learn and PyTorch

ML Engineer at Mu Sigma | Aug 2018 - Jan 2021
- Data analysis with Pandas and scikit-learn for retail forecasting models

SKILLS
Python, PyTorch, scikit-learn, NLP, Generative AI, LangChain, Embeddings, ChromaDB, Pandas, Docker, Kubernetes, GCP, SQL

PROJECTS
LLM Document Assistant
- RAG pipeline with LangChain and vector embeddings for document Q&A

EDUCATION
M.Tech in Computer Science, IISc Bangalore, 2018

CERTIFICATIONS
Google Cloud Certified Professional Machine Learning Engineer

ACHIEVEMENTS
Reduced model inference cost by 55% via quantization
""",
    "rahul_gupta.txt": """Rahul Gupta
Java Backend Developer

rahul.gupta@example.com | +91 98111 22334

SUMMARY
Java developer with 4 years of enterprise backend experience.

EXPERIENCE
Software Engineer at Accenture | Apr 2021 - Present
- Built Spring Boot microservices with Oracle DB
- REST API development and Kafka integration

Software Engineer at Infosys | Aug 2019 - Mar 2021
- Java, Spring, Hibernate development for banking clients

SKILLS
Java, Spring Boot, REST API, Oracle, SQL, Kafka, Git, Jenkins, Maven

EDUCATION
B.E. in Information Technology, VIT Vellore, 2019
""",
    "sara_khan.txt": """Sara Khan
Python Developer (Fresher)

sara.khan@example.com
+91 97654 32109

SUMMARY
Recent graduate passionate about backend development in Python.

INTERNSHIP
Python Developer Intern at Paytm | Jan 2023 - Jun 2023
- Built internal Flask tools and automated reports with Pandas

SKILLS
Python, Flask, SQL, MySQL, Pandas, Git, HTML, CSS

PROJECTS
Expense Tracker API
- Flask REST API with MySQL backend and JWT auth

EDUCATION
B.Tech in Computer Science, Amity University, 2023
""",
}
