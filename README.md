# image-ocr-validator

### Usage

If you are not using Docker, you will need pip and the dependencies listed in requirements.txt

```
./launch.sh https://google.com/ https://yahoo.com/
```

### Docker

#### Build (only once)
```
docker build -t img-ocr-validator .
```

#### Run
```
docker run --rm -it --user $(id -u):$(id -g) -v "$(pwd):/root/" -e URLS="https://google.com/ https://yahoo.com/" img-ocr-validator
```

### Options
```
usage: img-ocr-validator [-h] [-g] [-p] [-k] [-s SEVERITY] [-e EXCLUDE] [URL ...]

Launch flags for img-ocr-validator.

positional arguments:
  URL                   URLs to analyze.

options:
  -h, --help            show this help message and exit
  -g, --generate-report
                        Generate HTML reports.
  -p, --parse-only      Generate HTML reports from existing report.json.
  -k, --legacy-report   Use the legacy HTML reporter.
  -s SEVERITY, --severity SEVERITY
                        Only include <SEVERITY> or greater in the report. (Valid severities: INFO, WARN, ERROR)
  -e EXCLUDE, --exclude EXCLUDE
                        Exclude the presented css selectors.
```
