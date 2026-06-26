# PPL

C172N performance calculator with takeoff, landing, and cruise calculators.

## Run Locally

```bash
pip install -r requirements.txt
flask --app app run --host=0.0.0.0 --port=5000
```

Open:

```text
http://127.0.0.1:5000
```

## Synology Container Manager

Use Container Manager with the included `docker-compose.yml`.

The container uses the latest official Python image and maps:

```text
NAS port 8088 -> container port 5000
```

After starting the project, open:

```text
http://YOUR_NAS_IP:8088
```

For a DSM reverse proxy or custom domain, point it to:

```text
http://127.0.0.1:8088
```
