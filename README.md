# PropHub

To run without docker:

1. Create a virtual environment.

2. To install server dependencies, run `pip install -r requirements.txt` in your terminal.

3. To run the server, run `uvicorn server.main:app --reload` in your terminal.


To run with docker:

1. Run `docker build -t <image_name> .`

2. Run `docker run -d`
