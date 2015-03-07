# Порт проекта u16_speccy на отладочную плату Zr-Tech WXEDA

Порт оригинального проекта конфигурации Speccy для платы Reverse U16 [https://code.google.com/p/reverse-u16/](https://code.google.com/p/reverse-u16/), Автор оригинального проекта: MVV
``
## Модификация платы:

Плата достаточно бедно укомплектована, для полноценной работы проекта необходимо провести ряд модификаций с паяльником для того,
чтобы сделать поддержку SD-карты и задействовать освободившиеся пины (под SD-карту и вывод звука, в частности).

1. Необходимо выпаять 7-сегментный индикатор и впаять вместо него pin header 2x6
2. Необходимо выпаять IR-приемник и паять вместо него pin header 1x3
3. Необходимо выпаять ВЧ-разъем
4. Необходимо заменить (опционально) резисторные сборки RP10-RP12 300 Ом на сборки 0 Ом
5. Собрать shield-плату [https://github.com/andykarpov/wxeda-sdcard-shield](https://github.com/andykarpov/wxeda-sdcard-shield), которая будет служить адаптером SD-карты + линейный выход звука

Данная модификация также подходит для таких проектов:

1. Радио-86РК для WXEDA [https://github.com/andykarpov/radio-86rk-wxeda](https://github.com/andykarpov/radio-86rk-wxeda)
2. Специалист для WXEDA [https://github.com/andykarpov/specialist-wxeda](https://github.com/andykarpov/specialist-wxeda)
3. Вектор-06Ц для WXEDA [https://code.google.com/p/vector06cc/](https://code.google.com/p/vector06cc/) (svn-ветка **wxeda-cycloneiv**)

Фото девборды после модификаций:

![image](https://farm9.staticflickr.com/8563/16123145773_dfebd94346.jpg)

Фото девборды с SD-адаптером:

![image](https://farm4.staticflickr.com/3948/15601327551_425db1abcc.jpg)

## Подготовка:

В оригинальном проекте файл образов ПЗУ хранится в конфигурационной флеш-памяти и заливается через JTAG вместе с основной прошивкой в отдельные страницы этой флешки (с помощью jic).
Ввиду того, что на плате WXEDA стоит достаточно мелкая конфигурационная флеш (EPSC4), на нее не помещается весь образ.
Поэтому в данном проекте решено было использовать встроенную на плату SPI Flash ПЗУ Winbond W25Q32 объемом 4МБ.

### Запись ROM на W25Q32

Необходимо записать на встроенную SPI Flash Winbond W25Q32 образ roms/output.rom.
Так как у автора не было специаольного программатора, но была под рукой Raspberry Pi, было найдено решение, как практически безболезненно
прошить впаянную на девборку SPI флешку:

- В девборду заливается прошивка [https://github.com/andykarpov/speccy-wxeda-sdcard-bridge](https://github.com/andykarpov/speccy-wxeda-sdcard-bridge) через JTAG, которая реализует соединение пинов W25Q32 с внешними пинами гребенки
- Пины гребенки **2,3,4,5 (DI,DO,CLK,CS)**, подключенные (виртуально) к W25Q32 и **GND** (средний пин гребенки 1x3 от выпаянного IR-приемника) 
    соединяются с **GPIO** пинами Raspberry Pi (**19,21,23,24,25** соответственно). Подробнее: [http://flashrom.org/RaspberryPi](http://flashrom.org/RaspberryPi)
- На Raspberry Pi установлена последняя версия Raspbian
- На Raspberry Pi скачивается и устанавливается проект flashrom - [http://flashrom.org/Downloads](http://flashrom.org/Downloads) + необходимые зависимости для его сборки
- включается модуль ядра spi (через raspi-config или руками - modprobe spi_bcm2708 и modprobe spidev)
- заливка прошивки:
    - проверяем, находится ли флешка: `./flashrom -p linux_spi:dev=/dev/spidev0.0` 
    - если находится - заливаем: `./flashrom -p linux_spi:dev=/dev/spidev0.0 -w /путь/к/output.rom`
    - так как flashrom сравнивает размер флешки и образа, он найдет несоответствие output.rom с размером флешки
    - для этого дополняем образ output.rom необходимым количеством нулей: `dd if=/dev/zero of=zeroes.rom bs=количествобайт count=1`, затем доливаем этот zeroes.rom в 
    output.rom: `cat zeroes.rom >> output.rom`
    - теперь можно повторить заливку
    - успешная запись длится порядка 30 секунд

фото этапа программирования с помощью flashrom: 

![image](https://farm8.staticflickr.com/7619/16717196616_d40a3a308b.jpg)

### Подготовка SD-карты

- Взять чистую SD-карту, отформатированную в FAT16 или FAT32
- Записать в корень файл **softwares/FATALL.$C** (необходим для работы Z-Controller'а в меню GLUK "Fat boot")
- Скачать дистрибутив **ESXDOS** для divMMC [http://www.esxdos.org/](http://www.esxdos.org/), распаковать и переписать на SD-карту директории **BIN**, **SYS**, создать директорию **TMP**, скопировать в корень файл **ESXMMC.TAP**
- Записать необходимое количество Ваших образов TRD, SCL, TAP, можно распихивать их по вложенным директориям.

### Заливка jic в конфигурационную флеш девборды:

- Открыть проект в Quartus 13
- Открыть Programmer
- Выбрать подготовленный файл speccy_wxeda.jic
- Выбрать подключенный USB Blaster
- Запустить программирование
- После успешной заливки выключить и включить девборду
- Profit :)

## Использование Speccy на WXEDA и особенности реализации интерфейса к SD карте

Итак, после подачи питания на плату происходит следующее:

1. FPGA заливает в себя конфигурацию с конфигурационной флешки EPCS4 и стартует ее
2. Далее запускается конфигурация и управление передается loader'у;
3. Loader автоматически загружает содержимое флешки W25Q32 в специальную область ОЗУ (SDRAM), отведенную под хранение ПЗУ
4. Управление передается GLUK-у, у нас запускается GLUK-меню

Теперь есть несколько возможностей (с помощью Z-Controller или divMMC контроллера) для монтирования и запуска приложений / образов дисков.

P.S. Ввиду отсутствия на плате WXEDA микросхем часов реального времени и CMOS, в loader'е и проекте выключено обращение к соответствующим портам, сам loader не ждет нажатия на Enter и сразу после своей работы передает управление компьютеру.

### Использование Z-Controller

- В меню GLUK выбираем `fat boot`
- Появится меню выбора из одного пункта, выбираем `Z-Controller`
- Появится меню выбора из одного пункта, выбираем `FATALL`
- Запустится оболочка приложения FATALL
- С помощью нее можно монтировать и запускать образы TRD и SCL. Суть всей работы заключается в том, что есть 2 панели (слева - физическая дискета, справа - файловая система на SD карте). Так вот, справа налево (и наоборот) можно копировать образы, которые потом будут доступны, как будто в системе присутствует дисковод со вставленной дискетой данного образа. В каждый образ TDR на карточке можно заходить (по кнопке Enter) для просмотра содержимого. Также можно копировать пофайлово файлы между этими панелями.
- Особенности: примонтированный образ будет доступен и после сброса. так что его повторно можно не монтировать, а запускать либо через GLUK boot, либо через пункт меню TR-DOS, либо 
если зайти в 128-меню и перейти там в TR-DOS, также можно будет увидеть и пользоваться примонтированным диском. 


### Использование divMMC

- В меню GLUK выбираем нужный вариант ROM, напримем 128 или 48, грузимся в него
- нажимаем F6 (запуск divMMC)
- нажимаем и удерживаем Space + F5 (включение NMI)
- жмем сброс F4
- нажимаем F5 - появляется оболочка divMMC
- в этой оболочке можно выбирать образы TAP/TRD для их загрузки и автозапуска

### Особенности

1. Сброс по F4 всегда сбрасывается в выбранную конфигурацию (48, 128)
2. Глобальный сброс (по кнопке **S4**) всегда приводит к полному циклу загрузки девборды
3. Когда включен divMMC / NMI, даже после глобального сброса он помнит, что включен (TBD).
4. В проекте горячие клавиши переключения между турбо режимами 3.5/7/14 МГц вынесены на функциональные кнопки F1-F3
5. Проект всегда стартует в режиме 3.5 МГц по-умолчанию

### Рабочие функциональные кнопки

- F1 - режим 3.5 МГц
- F2 - режим 7.0 МГц
- F3 - режим 14.0 МГц
- F4 - CPU Reset
- F5 - NMI On/Off
- F6 - divMMC On/Off
- F7 - рамка (недоделанная)
- F11 - soundrive
- F12 - видео режим Spectrum/Pentagon

Приятного использования :)