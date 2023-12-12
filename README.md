# Lisp. Транслятор и модель

- Лебедев Вячеслав Владимирович, P33312
- lisp | acc | harv | hw | tick | struct | stream | port | pstr | prob1 | 8bit
- усложнение `8bit` не реализовано

## Язык программирования

### Синтаксис

```ebnf
<program>               := <expressions> EOF

<expressions>           := | <expressions> <expression>

<expression>            := <open-bracket> <bracketed-expression> <close-bracket> | <varname> | <literal>

<bracketed-expression>  :=  <function-definition> 
                            | <function-call> 
                            | <if-condition> 
                            | <binary-operation> 
                            | <unary-operator-expression>
                            | <assignment> 
                            | <loop-expression>
                            | <allocation>

<function-call>         := <varname> <arguments>

<arguments>             := | <arguments> <expression>

<function-definition>   := defun <varname> <open-bracket> <parameters> <close-bracket> <expressions>

<parameters>            := | <parameters> <varname>

<assignment>            := setq <varname> <expr>

<allocation>            := alloc <number-literal>

<if-condition>          := if <condition-expression> <true-expression> <false-expression>

<loop-expression>       := loop <condition-expression> <expressions> 

<binary-operator-expression> := <binary-operator> <expression> <expression>

<unary-operator-expression> := <unary-operator> <expression>

<binary-operator>       := store | mod | and | or | + | - | = | < | >

<unary-operator>        := not | put | load

<nullary-operator>      := get

<condition-expression>  := <expression>

<true-expression>       := <expression>

<false-expression>      := <expression>

<literal>               := <number-literal> | <string-literal> | <character-literal>

<number-literal>        := [0-9]+

<string-literal>        := "\w*"

<character-literal>     := '.'

<varname>               := [a-zA-Z\.]\w*
```

### Семантика

Каждая операция является `выражением`, т.е. в результате вычисления "возвращает" результат.
Выполнение программы представляет собой последовательное вычисление таких выражений.
Например, выражение `(+ 1 (+ 2 3))` вычисляется так: `(+ 1 (+ 2 3)) -> (+ 1 5) -> 6`.

`setq` - объявляет переменную (если не была объявлена) и присваивает ей значение.
Переменные имеют область видимости: глобальную - получают переменные объявленные снаружи функций,
а локальную - параметры функции и переменные, объявленные внутри ее определения.
При этом из глобальной области невозможно обратиться к локальным переменным функции,
а из функции невозможно обратиться к глобальным переменным.

Код в глобальной области представляет собой список выражений, которые будут вычислены последовательно.
Тело функций тоже представляет собой список выражений, которые вычисляются последовательно.
При этом результат вычисления последнего выражения - является результатом функции.

Ключевые слова:

- `get` - прочитать байт
- `put` - вывести байт
- `alloc` - выделить буфер в статической памяти
- `load` - прочитать слово из ячейки по адресу
- `store` - загрузить слово в ячейку по адресу
- `setq` - присвоить значение переменной (и/или объявить переменную)
- `defun` - объявить функцию
- `loop` - выражение-цикл, выполняющийся до тех пор, пока истинно первое выражение внутри его тела
- `if` - условное выражение, если первое выражение вычисляется в ненулевое значение, то будет результатом будет второе
  выражение, если нет - третье

Литералы:

- `"Hello, world"` - строковый литерал
- `'a'` - символьный литерал
- 42 - числовой литерал

Пример кода:

```text
; <- комментарий

; | объявление функции
; v 
(defun sum(a b)
    (setq result (+ a b))   ; <- объявление локальной переменной и присвоение ей значения
    result                  ; <- последнее выражение = результат функции 
)

(setq magic 42)                 ; <- объявление глобальной переменнй
(loop (> magic 0)               ; <- условие цикла
    (setq magic (- magic 1))    ; <- тело цикла
)
```

### Типы данных

Существует единственный тип - 32-битное знаковое число, интерпретация которого ложится на плечи программиста.
Так, например, `(alloc <number>)` - выделить буфер размера `<number>` в статической памяти, возвращает число -
адрес буфера - от `0` до `2^24-1` (результат вычисления строкового литерала аналогичен).

## Организация памяти

1. Память команд. Машинное слово - `32` бит. Реализуется списком словарей, описывающих инструкции (одно слово - одна
   команда). Размер адресного пространства - `2^24` слов.
2. Память данных. Машинное слово - `32` бит, знаковое. Линейное адресное пространство. Реализуется списком чисел. Размер
   адресного пространства - `2^24` слов.

### Регистры

- `AC` (Accumulator) - аккумулятор, вокруг которого строится вычисление
- `CR` (Command Register) - используется для хранения текущей исполняемой инструкции
- `IP` (Instruction Pointer) - указатель инструкций
- `DR` (Data Register) - регистр данных (для работы с памятью и вводом/выводом)
- `AR` (Address Register) - адресный регистр (используется при чтении/записи в память)
- `SP` (Stack Pointer) - указатель стека
- `FP` (Frame Pointer) - указатель фрейма
- `BR` (Buffer Pointer) - используется во время выполнения промежуточных операций при исполнении инструкций

Так как это модель аккумуляторного процессора, то пользователь может явно работать только с аккумулятором.
Но помимо этого есть команды, которые неявно взаимодействуют с другими регистрами (`pop` - декремент указателя стека,
`jmp` - присвоить значение указателю инструкций).

### Виды Адресации

- `Absolute` - абсолютная, указывается адрес, где находится значение: `value = MEM[address]`
- `Relative` - относительная, указывается регистр и смещение `value = MEM[register + offset]`
- `Relative Inderect` - косвенная относительная, указывается регистр и смещение: `value = MEM[MEM[register + offset]]`

В качестве регистра можно указывать `Stack Pointer` и `Frame Pointer`.
Относительная адресация используется для работы со стеком и локальными переменными функций.

Число команд - 20, поэтому код инструкции имеет размер 5 бит (20 < 32 = 2 ^ 5).
Также, так как типов адресации - 4, то на их кодирование требуется еще 2 бита.
И 1 бит необходим для кодирования регистра при относительной адресации.
Остается 24 бита. Из-за этого адресное пространство ограничивается 24 битами,
поэтому память данных также ограничена: ее максимальный объем - 16777216 32-битных слов.

Команды перехода отнесены в отдельную категорию. Для таких команд можно задать только абсолютный адрес и
это всегда адрес в памяти инструкций.

| Тип команды                 | Схема                                                  |
|-----------------------------|--------------------------------------------------------|
| `Default`                   | `[OPCODE: 5][RESERVED: 27]`                            |
| `Execution Flow`            | `[OPCODE: 5][RESERVED: 3][ADDRESS: 24]`                |
| `Absolute Address`          | `[OPCODE: 5][ADDRESSING: 2][RESERVED: 1][ADDRESS: 24]` |
| `Relative Address`          | `[OPCODE: 5][ADDRESSING: 2][REGISTER: 1][OFFSET: 24]`  |
| `Relative Inderect Address` | `[OPCODE: 5][ADDRESSING: 2][REGISTER: 1][OFFSET: 24]`  |

### Литералы

Каждый литерал является Lisp-выражением, таким образом в результате своего "вычисления" должен стать значением на стеке.

- строковые - сама строка помещается в статическую память, закодированную в pascal-style, после "вычисления" помещает
  адрес строки на стек
- числовые - при компиляции значение помещается в ячейку статической памяти, при "вычислении" на стек помещается
  число, вычитанное из статической памяти
- символьные - по организации в памяти аналогичны числовым литералам, по сути - являются макросом, чтобы не писать
  каждый раз ASCII код

### Размещение данных

```text
       Instruction memory
+------------------------------+
| 00  : nop  (program start)   |
|    ...                       |
| xx  : halt  (program stop)   |
|    ...                       |
| i   : nop  (function "foo")  |
| i+1 : function body          |
|    ...                       |
| j   : nop  (function "baz")  |
| j+1 : function body          |
|    ...                       |
+------------------------------+

          Data memory
+------------------------------+
| 00  : 42  (number literal)   |
|    ...                       |
| i   : 111 (char literal 'o') |
|    ...                       |
| j   : 5 (string literal)     |
| j+1 : 104 ('h')              |
| j+2 : 101 ('e')              |
| j+3 : 108 ('l')              |
| j+4 : 108 ('l')              |
| j+5 : 111 ('o')              |
|    ...                       |
| k   : 0 (static variable x)  |           ^
|    ...                       |           | 
| ff : ...                     | <- stack top
+------------------------------+
```

## Система Команд Процессора

### Набор инструкций

| №  | инструкция | эффект                              | тип         | описание                                                |
|----|------------|-------------------------------------|-------------|---------------------------------------------------------|
| 1  | `add A`    | `AC + MEM[A] -> AC`                 | с операндом | сложение знаковых числ                                  |
| 2  | `sub A`    | `AC - MEM[A] -> AC`                 | с операндом | вычитание знаковых числ                                 |
| 3  | `and A`    | `AC & MEM[A] -> AC`                 | с операндом | побитовое логическое "И"                                |
| 4  | `or A`     | `AC v MEM[A] -> AC`                 | с операндом | побитовое логическое "ИЛИ"                              |
| 5  | `not`      | `~AC -> AC`                         | безадресная | побитовое логическое "НЕ"                               |
| 6  | `ld A`     | `MEM[A] -> AC`                      | адресная    | загрузка значения в аккумулятор по адресу               |
| 7  | `st A`     | `AC -> MEM[A]`                      | адресная    | сохранение значения из аккумулятора по адресу           |
| 8  | `put`      | `AC -> IO`                          | безадресная | вывод значения из аккумулятора                          |
| 9  | `get`      | `IO -> AC`                          | безадресная | ввод значения в аккумулятор                             |
| 10 | `push`     | `SP - 1 -> SP`                      | безадресная | подъем указателя стека                                  |
| 11 | `pop`      | `SP + 1 -> SP`                      | безадресная | понижение указателя стека                               |
| 12 | `jmp A`    | `A -> IP`                           | перехода    | безусловный переход                                     |
| 13 | `jz A`     | `A -> IP, if AC == 0`               | перехода    | переход, если в аккумуляторе `0`                        |
| 14 | `call A`   | `IP -> STACK, FP -> STACK, A -> IP` | перехода    | вызов функции                                           |
| 15 | `ret`      | `STACK -> FP, STACK -> IP`          | безадресная | возврат из функции                                      |
| 16 | `ispos`    | `(AC > 0) -> AC`                    | безадресная | проверка, что в аккумуляторе строго положительное число |
| 17 | `isneg`    | `(AC < 0) -> AC`                    | безадресная | проверка, что в аккумуляторе строго отрицательное число |
| 18 | `iszero`   | `(AC == 0) -> AC`                   | безадресная | проверка, что в аккумуляторе `0`                        |
| 19 | `nop`      |                                     | безадресная | бездействие                                             |
| 20 | `halt`     |                                     | безадресная | остановка исполнения                                    |

### Исполнение инструкций

Исполнение инструкции проходит в 4 этапа:

1) `Instruction Fetch` (выборка инструкции) - из памяти инструкций выбирается текущая команда и увеличивается счетчик
   инструкций
2) `Address Fetch` (выборка адреса) - для адресных команд, команд с операндом и команд перехода
3) `Operand Fetch` (выборка операнда) - для команд с операндом
4) `Execution` (исполнение) - непосредственное исполнение команды

Instruction Fetch

```text
IMEM[IP] -> CR
IP + 1 -> IP
```

Address Fetch

```text
ABSOLUTE ADDRESS:
    CR[8:31] -> AR

RELATIVE ADDRESS:
    CR[8:31] + $reg -> AR

RELATIVE INDIRECT ADDRESS:
    CR[8:31] + $reg -> AR
    MEM[AR]         -> DR
    DR              -> AR

EXECUTION FLOW:
    CR[8:31] -> AR
```

Operand Fetch

```text
MEM[AR] -> DR
```

Execution

```text
add, sub, and, or:
    AC . DR -> AC

not:
    NOT(AC) -> AC
    
jmp:
    AR -> IP

jz:
    AR -> IP, if FLAGS[ZERO] == 1

call:
    AR      -> BR
    IP      -> DR       % save IP
    SP      -> AR
    DR      -> MEM[AR]
    SP - 1  -> SP
    FP      -> DR       % save FP
    SP      -> AR
    DR      -> MEM[AR]
    SP - 1  -> SP
    SP      -> FP
    BR      -> IP       % jump

ret:
    SP + 1  -> SP       % recover FP
    SP      -> AR
    MEM[AR] -> DR
    DR      -> FP
    SP + 1  -> SP       % recover IP
    SP      -> AR
    MEM[AR] -> DR
    DR      -> IP

ld:
    DR      -> AC

st:
    AC      -> DR
    DR      -> MEM[AR]
 
push:
    SP - 1  -> SP
 
pop:
    SP + 1  -> SP

put:
    AC      -> DR
    DR      -> IO

get:
    IO      -> DR
    DR      -> AC

ispos:
    (AC > 0) -> AC

isneg:
    (AC < 0) -> AC

iszero:
    (AC == 0) -> AC
```

### Соглашение о вызове функций

**Вызов**

Для исполнения Lisp функции, объявленной при помощи `defun`

`Caller`:

- на стек помещаются аргументы функции после вычисления `k` выражений (число аргументов всегда **равно** числу
  параметров функции)
- вызов инструкции `call A`:
    - на стек помещается адрес возврата (текущий `IP`)
    - сохраняется текущий указатель фрейма `FP`
    - устанавливается новый указатель фрейма функции: `SP -> FP`
    - происходит переход к функции: `A -> IP`

`Callee`:

- на стеке выделяется неинициализированная память для локальных переменных функции

**Выполнение функции и результат**

Выражения тела функции вычисляются последовательно. Последнее выражение - результат функции, помещается на стек.

**Возврат**

Результат функции - всегда **одно** слово, помещенное на стек

`Callee`:

- результат снимается со стека и сохраняется в аккумулятор
- снимаются локальные переменные - производится `n` вызовов `pop`
- вызов `ret` - восстанавливается предыдущий `Frame Pointer` и `Instruction Pointer`

`Caller`:

- снимаются аргументы функции - производится `k` вызовов `pop`
- результат из аккумулятора помещается на стек

Доступ к локальным переменным осуществляется при помощи относительной адресации в сторону младших адресов
`address_of(local_var[i]) = fp - i, где i = [0..n-1]`.

Доступ к аргументам тоже осуществляется относительно указателя фрейма,
но в сторону старших адресов: `address_of(arg[i]) = fp - i + k + 2, где i = [0..k-1]`
(смещение +2 появляется из-за того, что `FP` расположен на 2 адреса выше последнего параметра).

```text
0x0000  | ...            | 
        :                :
        |                | <- SP
        | result         | 
        | local var n-1  |
        | ...            |
        | local var 0    | <- FP    % frame i + 1
        +----------------+
        | old frame ptr  |
        | return address |
        | arg k-1        |
        | ...            |
        | arg 0          |
        | ...            |          % frame i
        :                :
0xffff  | ...            |
```

### Кодирование инструкций и данных

- Машинный код сериализуется в список JSON.
- Один элемент списка - одно машинное слово, одна инструкция
- Индекс списка - адрес инструкции, используется при командах перехода

Пример:

```json
[
  {
    "opcode": "ld",
    "address": {
      "type": "absolute",
      "value": 0
    },
    "debug": "variable value [char]",
    "index": 11
  },
  {
    "opcode": "sub",
    "address": {
      "type": "relative",
      "register": "sp",
      "offset": 1
    },
    "index": 15
  },
  {
    "opcode": "jz",
    "address": {
      "type": "control-flow",
      "value": 98
    },
    "debug": "jump if false",
    "index": 84
  },
  {
    "opcode": "push",
    "index": 12
  }
]
```

где:

- `opcode` - строка с кодом операции
- `address` - для команд перехода - адрес инструкции, для адресных команд - адрес (абсолютный, относительный,
  косвенный)
- `debug`, `index` - дополнительная информация для дебага, не используется при исполнении инструкции

Типы данных описаны в [isa](translator/isa.py), где:

- `Opcode` - перечисление кодов операций;
- `Addressing` - перечисление типов адресации
- `Register` - перечисление регистров, используемых для относительной адресации

Статическая область памяти сериализуется в виде JSON массива чисел

Пример:
(`"hello"` закодированное в виде Pascal строки)

```json
[
  5,
  104,
  101,
  108,
  108,
  111
]
```

## Транслятор

Интерфейс командной строки: translator.py <input_file> <target_file>

Состоит из 4 основных файлов:

- [lexer.py](lexer.py)
- [parsing.py](parsing.py)
- [compiler.py](compiler.py)
- [translator.py](translator.py)

### Лексер

Содержит перечисления для токенов, а также соответствующие им regex паттерны, описанные в виде элементарных регулярных
выражений.
А также два класса - `Lexer` и `Token`. `Lexer` содержит основную логику по разбиению исходного кода на токены.
А класс `Token` в себе инкапсулирует информацию о токене (тип, дополнительная информация).

### Парсер

На основе токенов, полученных от лексера формирует абстрактное синтаксическое дерево.
Внутри файла объявлены классы - узлы дерева. А также класс `Parser`, содержащий в себе основную логику по
его формированию.

Парсер объединяет токены в узлы дерева по правилам, описанным выше в форме Бэкуса-Нуара.

### Компилятор

Получает на вход абстрактное синтаксическое дерево от парсера, на основе которого формирует
линейный код в виде списка инструкций, описанных в [isa.py](isa.py).

Внутри файла находится 3 основных класса:

- `DataSegment` - управляет размещением статических данных
- `TextSegment` - управляет размещением инструкций в сегменте кода
- `Compiler` - содержит основную логику по преобразованию `AST` в код

Основное правило компиляции - каждое Lisp-выражение должно быть преобразовано в
значение на стеке. Таким образом, каждое выражение помещает результат на стек, а
вызвавшее его выражение - снимает его и использует в вычислении.

Иногда это может привести к избыточной работе со стеком, но зато упрощает процесс
написания компилятора и избавляет от необходимости думать о состоянии аккумулятора
и размещении переменных.

### Транслятор

- соединяет исходный код со стандартной библиотекой
- использует перечисленные файлы для преобразования исходного кода
- обеспечивает работу с командной строкой

TODO: оптимизации вызовов функций и т д

## Модель процессора

Интерфейс командной строки: machine.py <machine_code_file> <input_file>

Реализовано в модуле: [machine](machine.py).

### Data Path

![img.png](images/img.png)

Реализован в классе `DataPath`.

`data_memory` - однопортовая память, поэтому либо читаем, либо пишем.

Сигналы реализованы в виде методов класса:

- `port_read` - прочитать значение из порта в регистр `DR`
- `port_write` - записать значение в порт из регистра `DR`
- `data_read` - прочитать значение из памяти в регистр `DR` по адресу из регистра `AR`
- `data_write` - записать значение в память по адресу из регистра `AR` в регистр `DR`
- `alu_signal` - передать в АЛУ сигнал на выполнение операции `AluOpSig` и опционально: инвертировать операнды, сделать
  инкремент результата

Флаги:

- `accumulator zero` - отражает наличие нулевого значения в аккумуляторе.
- `instruction address` - текущий адрес инструкций

### Control Unit

![img_1.png](images/img_1.png)

Реализован в классе `ControlUnit`.

- hardwired (реализовано полностью на Python).
- метод `tick` моделирует выполнение одного такта
- внутренняя переменная `_cycle_tick` показывает такт выполнения текущего цикла
- внутренняя переменная `_execution_cycle` показывает текущий цикл (выборка команды, адреса, операнда, выполнение)
- каждый такт происходит либо переход на следующий такт цикла, либо переход на следующий цикл

Сигналы:

- `latch_command_register` - защелкнуть новое значение текущей команды
- `alu_call` - запускает работу АЛУ с нужными параметрами

Особенности работы модели:

- Цикл симуляции осуществляется в функции `simulation`
- Шаг моделирования соответствует одному такту
- Для журнала состояний процессора используется стандартный модуль logging
- Количество инструкций для моделирования лимитировано.
- Остановка моделирования осуществляется при:
    - превышении лимита количества выполняемых инструкций;
    - исключении `StopIteration` -- если выполнена инструкция `HALT`.

## Тестирование

1) [hello](examples/hello.clisp)
2) [cat](examples/cat.clisp)
3) [hello_user_name](examples/hello_user_name.clisp)
4) [problem 1](examples/problem-1.clisp)

Интеграционные тесты реализованы тут [integration_test](integration_test.py) в двух вариантах:

- через golden tests, конфигурация которых лежит в папке [golden](golden)
- через unittest

CI:

```yml
lab3:
  stage: test
  image:
    name: ryukzak/python-tools
    entrypoint: [ "" ]
  script:
    - poetry install
    - coverage run -m pytest --verbose
    - find . -type f -name "*.py" | xargs -t coverage report
    - ruff format --check .
    - ruff check .
```

Пример использования и журнал работы процессора на примере

```yml
in_source: |-
  ; cat -- печатать данные, поданные на вход симулятору через файл ввода
  (setq char (get))
  (loop (is-not (= 0 char))      ; EOF == 0
      (put char)              ; put = print char, get = read char
      (setq char (get))
  )
in_stdin: |-
  foo
out_log: |
  DEBUG   machine:simulation    TICK:   0 CR: None DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2047 IP:0 DR:0 AR:0]
  DEBUG   machine:simulation    TICK:   2 CR: {'opcode': NOP, 'debug': 'program start', 'index': 0} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2047 IP:1 DR:0 AR:0]
  DEBUG   machine:simulation    TICK:   5 CR: {'opcode': GET, 'debug': 'nullary operator', 'index': 1} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2047 IP:2 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:   7 CR: {'opcode': PUSH, 'index': 2} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2046 IP:3 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:  11 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 3} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2046 IP:4 DR:102 AR:2047]
  DEBUG   machine:simulation    TICK:  15 CR: {'opcode': LD, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 4} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2046 IP:5 DR:102 AR:2047]
  DEBUG   machine:simulation    TICK:  19 CR: {'opcode': ST, 'address': {'type': 'absolute', 'value': 0}, 'index': 5} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2046 IP:6 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:  21 CR: {'opcode': POP, 'index': 6} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2047 IP:7 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:  23 CR: {'opcode': NOP, 'debug': 'loop start', 'index': 7} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2047 IP:8 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:  27 CR: {'opcode': LD, 'address': {'type': 'absolute', 'value': 1}, 'debug': 'number literal [0]', 'index': 8} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2047 IP:9 DR:0 AR:1]
  DEBUG   machine:simulation    TICK:  29 CR: {'opcode': PUSH, 'index': 9} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2046 IP:10 DR:0 AR:1]
  DEBUG   machine:simulation    TICK:  33 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 10} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2046 IP:11 DR:0 AR:2047]
  DEBUG   machine:simulation    TICK:  37 CR: {'opcode': LD, 'address': {'type': 'absolute', 'value': 0}, 'debug': 'variable value [char]', 'index': 11} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2046 IP:12 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:  39 CR: {'opcode': PUSH, 'index': 12} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2045 IP:13 DR:102 AR:0]
  DEBUG   machine:simulation    TICK:  43 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 13} DATA PATH: REGISTERS: [AC:102 FP:0 BR:0 SP:2045 IP:14 DR:102 AR:2046]
  DEBUG   machine:simulation    TICK:  47 CR: {'opcode': LD, 'address': {'type': 'relative', 'register': 'sp', 'offset': 2}, 'debug': 'binary operation [T_EQUALS]', 'index': 14} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2045 IP:15 DR:0 AR:2047]
  DEBUG   machine:simulation    TICK:  51 CR: {'opcode': SUB, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 15} DATA PATH: REGISTERS: [AC:-102 FP:0 BR:0 SP:2045 IP:16 DR:102 AR:2046]
  DEBUG   machine:simulation    TICK:  53 CR: {'opcode': IS_ZERO, 'index': 16} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2045 IP:17 DR:102 AR:2046]
  DEBUG   machine:simulation    TICK:  55 CR: {'opcode': POP, 'index': 17} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2046 IP:18 DR:102 AR:2046]
  DEBUG   machine:simulation    TICK:  59 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 18} DATA PATH: REGISTERS: [AC:0 FP:0 BR:0 SP:2046 IP:19 DR:0 AR:2047]
  DEBUG   machine:simulation    TICK:  72 CR: {'opcode': CALL, 'address': {'type': 'control-flow', 'value': 70}, 'debug': 'function call [is-not]', 'index': 19} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2044 IP:70 DR:0 AR:2045]
  DEBUG   machine:simulation    TICK:  74 CR: {'opcode': NOP, 'debug': 'function [is-not]', 'index': 70} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2044 IP:71 DR:0 AR:2045]
  DEBUG   machine:simulation    TICK:  78 CR: {'opcode': LD, 'address': {'type': 'relative', 'register': 'fp', 'offset': 3}, 'debug': 'variable value [b]', 'index': 71} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2044 IP:72 DR:0 AR:2047]
  DEBUG   machine:simulation    TICK:  80 CR: {'opcode': PUSH, 'index': 72} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2043 IP:73 DR:0 AR:2047]
  DEBUG   machine:simulation    TICK:  84 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 73} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2043 IP:74 DR:0 AR:2044]
  DEBUG   machine:simulation    TICK:  88 CR: {'opcode': LD, 'address': {'type': 'absolute', 'value': 9}, 'debug': 'number literal [0]', 'index': 74} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2043 IP:75 DR:0 AR:9]
  DEBUG   machine:simulation    TICK:  90 CR: {'opcode': PUSH, 'index': 75} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2042 IP:76 DR:0 AR:9]
  DEBUG   machine:simulation    TICK:  94 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 76} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2042 IP:77 DR:0 AR:2043]
  DEBUG   machine:simulation    TICK:  98 CR: {'opcode': LD, 'address': {'type': 'relative', 'register': 'sp', 'offset': 2}, 'debug': 'binary operation [T_EQUALS]', 'index': 77} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2042 IP:78 DR:0 AR:2044]
  DEBUG   machine:simulation    TICK: 102 CR: {'opcode': SUB, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 78} DATA PATH: REGISTERS: [AC:0 FP:2044 BR:70 SP:2042 IP:79 DR:0 AR:2043]
  DEBUG   machine:simulation    TICK: 104 CR: {'opcode': IS_ZERO, 'index': 79} DATA PATH: REGISTERS: [AC:1 FP:2044 BR:70 SP:2042 IP:80 DR:0 AR:2043]
  DEBUG   machine:simulation    TICK: 106 CR: {'opcode': POP, 'index': 80} DATA PATH: REGISTERS: [AC:1 FP:2044 BR:70 SP:2043 IP:81 DR:0 AR:2043]
  DEBUG   machine:simulation    TICK: 110 CR: {'opcode': ST, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 81} DATA PATH: REGISTERS: [AC:1 FP:2044 BR:70 SP:2043 IP:82 DR:1 AR:2044]
  DEBUG   machine:simulation    TICK: 114 CR: {'opcode': LD, 'address': {'type': 'relative', 'register': 'sp', 'offset': 1}, 'index': 82} DATA PATH: REGISTERS: [AC:1 FP:2044 BR:70 SP:2043 IP:83 DR:1 AR:2044]
  DEBUG   machine:simulation    TICK: 117 CR: {'opcode': JZ, 'address': {'type': 'control-flow', 'value': 88}, 'debug': 'jump if false', 'index': 83} DATA PATH: REGISTERS: [AC:1 FP:2044 BR:70 SP:2043 IP:84 DR:88 AR:2044]
  ...
out_stdout: |
  source LoC: 93 code instr: 97 static memory: 12
  ============================================================
  foo
  instruction count: 243 ticks: 818
out_code: |-
  {"code": [{"opcode": "nop", "debug": "program start", "index": 0},
   {"opcode": "get", "debug": "nullary operator", "index": 1},
   {"opcode": "push", "index": 2},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 3},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 4},
   {"opcode": "st", "address": {"type": "absolute", "value": 0}, "index": 5},
   {"opcode": "pop", "index": 6},
   {"opcode": "nop", "debug": "loop start", "index": 7},
   {"opcode": "ld", "address": {"type": "absolute", "value": 1}, "debug": "number literal [0]", "index": 8},
   {"opcode": "push", "index": 9},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 10},
   {"opcode": "ld", "address": {"type": "absolute", "value": 0}, "debug": "variable value [char]", "index": 11},
   {"opcode": "push", "index": 12},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 13},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 2}, "debug": "binary operation [T_EQUALS]", "index": 14},
   {"opcode": "sub", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 15},
   {"opcode": "iszero", "index": 16},
   {"opcode": "pop", "index": 17},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 18},
   {"opcode": "call", "address": {"type": "control-flow", "value": 70}, "debug": "function call [is-not]", "index": 19},
   {"opcode": "pop", "debug": "local allocation clear", "index": 20},
   {"opcode": "push", "index": 21},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 22},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 23},
   {"opcode": "jz", "address": {"type": "control-flow", "value": 39}, "debug": "jump out of loop", "index": 24},
   {"opcode": "pop", "debug": "clear compare", "index": 25},
   {"opcode": "ld", "address": {"type": "absolute", "value": 0}, "debug": "variable value [char]", "index": 26},
   {"opcode": "push", "index": 27},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 28},
   {"opcode": "put", "address": {"type": "relative", "register": "sp", "offset": 1}, "debug": "unary operation [T_KEY_PUT]", "index": 29},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 30},
   {"opcode": "pop", "index": 31},
   {"opcode": "get", "debug": "nullary operator", "index": 32},
   {"opcode": "push", "index": 33},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 34},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 35},
   {"opcode": "st", "address": {"type": "absolute", "value": 0}, "index": 36},
   {"opcode": "pop", "index": 37},
   {"opcode": "jmp", "address": {"type": "control-flow", "value": 7}, "debug": "jump loop begin", "index": 38},
   {"opcode": "nop", "debug": "loop after", "index": 39},
   {"opcode": "pop", "index": 40},
   {"opcode": "ld", "address": {"type": "absolute", "value": 2}, "debug": "number literal [0]", "index": 41},
   {"opcode": "push", "index": 42},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 43},
   {"opcode": "pop", "index": 44},
   {"opcode": "ld", "address": {"type": "absolute", "value": 3}, "debug": "number literal [0]", "index": 45},
   {"opcode": "push", "index": 46},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 47},
   {"opcode": "pop", "index": 48},
   {"opcode": "ld", "address": {"type": "absolute", "value": 4}, "debug": "number literal [0]", "index": 49},
   {"opcode": "push", "index": 50},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 51},
   {"opcode": "pop", "index": 52},
   {"opcode": "ld", "address": {"type": "absolute", "value": 5}, "debug": "number literal [0]", "index": 53},
   {"opcode": "push", "index": 54},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 55},
   {"opcode": "pop", "index": 56},
   {"opcode": "ld", "address": {"type": "absolute", "value": 6}, "debug": "number literal [0]", "index": 57},
   {"opcode": "push", "index": 58},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 59},
   {"opcode": "pop", "index": 60},
   {"opcode": "ld", "address": {"type": "absolute", "value": 7}, "debug": "number literal [0]", "index": 61},
   {"opcode": "push", "index": 62},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 63},
   {"opcode": "pop", "index": 64},
   {"opcode": "ld", "address": {"type": "absolute", "value": 8}, "debug": "number literal [0]", "index": 65},
   {"opcode": "push", "index": 66},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 67},
   {"opcode": "pop", "index": 68},
   {"opcode": "halt", "debug": "program end", "index": 69},
   {"opcode": "nop", "debug": "function [is-not]", "index": 70},
   {"opcode": "ld", "address": {"type": "relative", "register": "fp", "offset": 3}, "debug": "variable value [b]", "index": 71},
   {"opcode": "push", "index": 72},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 73},
   {"opcode": "ld", "address": {"type": "absolute", "value": 9}, "debug": "number literal [0]", "index": 74},
   {"opcode": "push", "index": 75},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 76},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 2}, "debug": "binary operation [T_EQUALS]", "index": 77},
   {"opcode": "sub", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 78},
   {"opcode": "iszero", "index": 79},
   {"opcode": "pop", "index": 80},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 81},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 82},
   {"opcode": "jz", "address": {"type": "control-flow", "value": 88}, "debug": "jump if false", "index": 83},
   {"opcode": "ld", "address": {"type": "absolute", "value": 10}, "debug": "number literal [1]", "index": 84},
   {"opcode": "push", "index": 85},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 86},
   {"opcode": "jmp", "address": {"type": "control-flow", "value": 92}, "index": 87},
   {"opcode": "nop", "debug": "if false", "index": 88},
   {"opcode": "ld", "address": {"type": "absolute", "value": 11}, "debug": "number literal [0]", "index": 89},
   {"opcode": "push", "index": 90},
   {"opcode": "st", "address": {"type": "relative", "register": "sp", "offset": 1}, "index": 91},
   {"opcode": "st", "address": {"type": "relative", "offset": 2, "register": "sp"}, "debug": "after if", "index": 92},
   {"opcode": "pop", "index": 93},
   {"opcode": "ld", "address": {"type": "relative", "register": "sp", "offset": 1}, "debug": "save result", "index": 94},
   {"opcode": "pop", "debug": "clear result", "index": 95},
   {"opcode": "ret", "index": 96}],
   "data": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]}
```

Пример проверки исходного кода:

```text
$ poetry run pytest . -v --update-goldens
====================================================================== test session starts ======================================================================
platform linux -- Python 3.11.0rc1, pytest-7.4.3, pluggy-1.3.0 -- /[xxx]/.venv/bin/python
cachedir: .pytest_cache
rootdir: /[xxx]
configfile: pyproject.toml
plugins: golden-0.2.2
collected 15 items                                                                                                                                              

integration_test.py::test_translator_and_machine[golden/cat.yml] PASSED                                                                                   [  6%]
integration_test.py::test_translator_and_machine[golden/hello_user_name.yml] PASSED                                                                       [ 13%]
integration_test.py::test_translator_and_machine[golden/problem-1.yml] PASSED                                                                             [ 20%]
integration_test.py::test_translator_and_machine[golden/hello.yml] PASSED                                                                                 [ 26%]
integration_test.py::TestLexer::test_unknown_tokens PASSED                                                                                                [ 33%]
integration_test.py::TestLexer::test_wrong_char_literal PASSED                                                                                            [ 40%]
integration_test.py::TestLexer::test_wrong_string_literal PASSED                                                                                          [ 46%]
integration_test.py::TestParser::test_allocation PASSED                                                                                                   [ 53%]
integration_test.py::TestParser::test_binary PASSED                                                                                                       [ 60%]
integration_test.py::TestParser::test_function_call PASSED                                                                                                [ 66%]
integration_test.py::TestParser::test_function_definition PASSED                                                                                          [ 73%]
integration_test.py::TestParser::test_if_condition PASSED                                                                                                 [ 80%]
integration_test.py::TestParser::test_loop PASSED                                                                                                         [ 86%]
integration_test.py::TestParser::test_nullary PASSED                                                                                                      [ 93%]
integration_test.py::TestParser::test_unary PASSED                                                                                                        [100%]

====================================================================== 15 passed in 0.92s =======================================================================

$ poetry run ruff check .
$ poetry run ruff format .
7 files left unchanged
```

| ФИО                           | <алг>                      | <LoC> | <code байт> | <code инстр.> | <инстр.> | <такт.> | <вариант>                                                                              |
|-------------------------------|----------------------------|-------|-------------|---------------|----------|---------|----------------------------------------------------------------------------------------|
| Лебедев Вячеслав Владимирович | hello                      | 89    | -           | 105           | 646      | 2153    | lisp \| acc \| harv \| hw \| tick \| struct \| stream \| port \| pstr \| prob1 \| 8bit |
| Лебедев Вячеслав Владимирович | cat                        | 93    | -           | 97            | 243      | 818     | lisp \| acc \| harv \| hw \| tick \| struct \| stream \| port \| pstr \| prob1 \| 8bit |
| Лебедев Вячеслав Владимирович | hello_user_name            | 97    | -           | 315           | 2114     | 7103    | lisp \| acc \| harv \| hw \| tick \| struct \| stream \| port \| pstr \| prob1 \| 8bit |
| Лебедев Вячеслав Владимирович | prob1. Multiples of 3 or 5 | 100   | -           | 911           | 2577133  | 8475909 | lisp \| acc \| harv \| hw \| tick \| struct \| stream \| port \| pstr \| prob1 \| 8bit |
