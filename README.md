# Table Extraction from pdf file

To extract tables from pdfs use
http://127.0.0.1:8000/api/v1/pdfs/extract-table/ (POST) with keyword "file" in payload.

It will extract all the tables and save is at csv file in media/csv directory, filename will be the hash created.

To check the status of pdf file use
http://127.0.0.1:8000/api/v1/pdfs/status/a693998ff2a475d128c11644fbf02374249f08ac134d526a4d9b913d8b5834a5/ (GET)

To get list of all pdfs use
http://127.0.0.1:8000/api/v1/pdfs/list/ (GET)

To run the application 
1. Create database as stated in .env.sample file
2. python manage.py makemigrations
3. python manage.py migrate
4. python manage.py migrate (To run server)

To containerize the application and run in docker environment
1. Change the DB_HOST=db in .env file
2. Provide permission to entrypoint.sh file
               chmod +x entrypoint.sh
3. Then to create image
               docker compose up --build
4. To remove all images with containers 
               docker compose down --rmi all
