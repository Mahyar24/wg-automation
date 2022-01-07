# wg-automation
Run this code for adding a new peer to your WireGuard server.

## Installation

First, you need to install "QRencode". 

```bash
sudo apt-get install qrencode
```

Then, use the [git](https://git-scm.com/downloads) to clone this repository.

```bash
git clone https://github.com/Mahyar24/wg-automation && cd wg-automation;
```


## Usage

```bash
sudo python3.9 main.py
```
This will ask you for the peer's name and after that it will make a directory with the same name which incude both the `.conf` file and QR-code picture.

P.S: You must have superuser access to run this program. Compatible with python3.9+.


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Contact me: <OSS@Mahyar24.com> :)

## License
[GNU GPLv3 ](https://choosealicense.com/licenses/gpl-3.0/)
