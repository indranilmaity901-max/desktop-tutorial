FROM python:3.12-windowsservercore

WORKDIR /agent
COPY agent-desktop /agent
RUN pip install -r requirements.txt
CMD ["python", "-m", "windows_agent.main"]
