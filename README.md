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
Usage: ImgOCRValidator.py [args] <URLS>
 -h, -?, --help ....... Show all args.
 -g ................... Generate HTML report.
 -p ................... Generate HTML report from existing report.json.
 -k ................... Use the legacy HTML reporter.
```
