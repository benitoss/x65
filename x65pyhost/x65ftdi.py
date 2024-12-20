import pyftdi.spi

# Documenation pyftdi: SPI API
# https://eblot.github.io/pyftdi/api/spi.html

class X65Ftdi:
    # Definitions of pins of the FTDI FT2232H in the OpenX65 motherboard.
    # // bit masks of the signals on ADBUSx (low byte)
    PIN_SCK  = 0x0001
    PIN_MOSI = 0x0002
    PIN_MISO = 0x0004
    PIN_NORAFCSN = 0x0010         # // ADBUS4 (GPIOL0) (FLASHCSN)
    PIN_NORADONE = 0x0040           # // ADBUS6 (GPIOL2)
    PIN_NORARSTN = 0x0080         # // ADBUS7 (GPIOL3)
    # // bit masks of the signals on ACBUSx (high byte)
    PIN_ICD2NORAROM = 0x0100			#// ACBUS0
    PIN_ICDCSN = 0x0200			        #// ACBUS1
    PIN_AURARSTN = 0x0400		        #// ACBUS2 (was ICD2VERAROM)
    PIN_AURAFCSN = 0x0800			    #// ACBUS3 (was VERA2FCS)
    PIN_VERAFCSN = 0x1000			    #// ACBUS4
    PIN_CPUTYPE02 = 0x2000              #// ACBUS5
    PIN_VAFCDONE = 0x4000			    #// ACBUS6 (was VERADONE)
    PIN_VERARSTN = 0x8000			    #// ACBUS7

    PINS_ALL = PIN_NORAFCSN | PIN_NORADONE | PIN_NORARSTN | PIN_ICD2NORAROM | PIN_ICDCSN | PIN_AURARSTN | PIN_AURAFCSN | PIN_VERAFCSN | PIN_VAFCDONE | PIN_VERARSTN | PIN_CPUTYPE02

    def __init__(self, url = 'ftdi://ftdi:2232/1', log_file_name=None):
        if url is not None:
            self.openFtdi(url)
        # open log file?
        if log_file_name is not None:
            self.logf = open(log_file_name, 'a')
            self.logf.write('\n\nStart of log\n')
        else:
            self.logf = None

    def openFtdi(self, url = 'ftdi://ftdi:2232/1'):
        # Instantiate a SPI controller
        self.spi = pyftdi.spi.SpiController()

        # Configure the first interface (IF/1) of the first FTDI device as a
        # SPI master
        self.spi.configure(url)

        # Get a SPI port to a SPI slave w/ /CS on A*BUS3 and SPI mode 0 @ 6MHz
        self.slave = self.spi.get_port(cs=0, freq=1E6, mode=0)

        # Get GPIO port to manage extra pins, use A*BUS4 as GPO, A*BUS4 as GPI
        self.gpio = self.spi.get_gpio()

        self.pinout_idle()

    # // configure the high-byte (ACBUSx) to route SPI to the ICD,
    # // and keep ICD high (deselect).
    def pinout_idle(self):
        # for all GPIOs, configure just ICD2NORAROM and ICDCSN as outputs
        self.gpio.set_direction(X65Ftdi.PINS_ALL,
                            X65Ftdi.PIN_ICD2NORAROM | X65Ftdi.PIN_ICDCSN)
        # // drive low ICD2NORAROM (this unroutes SPI to flash),
        # // drive high ICDCSN, all others are IN.
        self.gpio.write(X65Ftdi.PIN_ICDCSN)


    # // ICD chip select assert
    # // should only happen while ICD2NORAROM=Low
    def icd_chip_select(self):
        # // drive low ICD2NORAROM (this unroutes SPI to flash),
        # // drive low ICDCSN to activate the ICD
        self.gpio.write(0)
        if self.logf is not None:
            self.logf.write('SELECT\n')
        # mpsse_set_gpio_high(VERA2FCSN | VERAFCSN | VERADONE | VERARSTN, 
        # 			ICD2NORAROM | ICDCSN);

    # // ICD chip select deassert
    def icd_chip_deselect(self):
        # // drive low ICD2NORAROM (this unroutes SPI to flash),
        # // drive high ICDCSN to de-activate the ICD
        self.gpio.write(X65Ftdi.PIN_ICDCSN)
        if self.logf is not None:
            self.logf.write('DESEL\n')
        # mpsse_set_gpio_high(ICDCSN | VERA2FCSN | VERAFCSN | VERADONE | VERARSTN, 
        # 			ICD2NORAROM | ICDCSN);

    def spiexchange(self, out, readlen):
        if self.logf is not None:
            self.logf.write('  EX.out {}\n'.format( ''.join('{:02x} '.format(x) for x in out) ))
        read = self.slave.exchange(out, readlen, start=False, stop=False, duplex=True)
        if self.logf is not None:
            self.logf.write('  EX.inp {}\n'.format( ''.join('{:02x} '.format(x) for x in read) ))
        return read

    def spiwriteonly(self, out):
        if self.logf is not None:
            self.logf.write('  WO.out {}\n'.format( ''.join('{:02x} '.format(x) for x in out) ))
        self.slave.write(out,  start=False, stop=False)

    # Read the CPUTYPE02 signal available on FTDI pin ACBUS5.
    # Returns TRUE in case of 65C02, and FALSE in case of 65C816 CPU is installed on the target board.
    def is_cputype02(self):
        return (self.gpio.read() & X65Ftdi.PIN_CPUTYPE02) != 0
