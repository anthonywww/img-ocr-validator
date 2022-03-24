# image-ocr-validator

### Usage

If you are not using Docker, you will need pip and the dependencies listed in requirements.txt

```
./launch.sh https://www.google.com/ https://www.yahoo.com/
```

### Docker

#### Build (only once)
```
docker build -t img-ocr-validator .
```

#### Run
```
docker run --rm -it --user $(id -u):$(id -g) -v "$(pwd):/root/" -e ARGS="-g https://www.google.com/ https://www.yahoo.com/" img-ocr-validator
```

### Options
```
usage: img-ocr-validator [-h] [-g] [-p] [-s SEVERITY] [--exclude EXCLUDE] [--allow-duplicates] [-c COOKIES] [URL ...]

Launch flags for img-ocr-validator.

positional arguments:
  URL                   URLs to analyze.

options:
  -h, --help            show this help message and exit
  -g, --generate-report
                        Generate HTML reports.
  -p, --parse-only      Generate HTML reports from existing report.json.
  -s SEVERITY, --severity SEVERITY
                        Only include <SEVERITY> or greater in the report. (Valid severities: NONE, INFO, WARN, ERROR)
  --exclude EXCLUDE     Exclude the presented css selectors. (Separated by , (commas))
  --allow-duplicates    Ignore duplicate resource id's (may cause unexpected results!)
  -c COOKIES, --cookies COOKIES
                        Set cookies to a Netscape HTTP Cookie File
```
