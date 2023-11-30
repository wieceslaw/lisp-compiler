Синтаксис:
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

<varname>               := [a-zA-Z]\w*
```

Операции:
- `get` - прочитать значение извне
- `put` - вывести значение
- `alloc` - выделить буфер в статической памяти
- `not` - логическое "не", 0 -> 1, <ненулевое число> -> 0
- `load` - прочитать значение из ячейки по адресу
- `store` - загрузить значение в ячейку по адресу
- `setq` - присвоить значение переменной (и/или объявить переменную)
- `defun` - объявить функцию
- `42` - числовой литерал
- `"Hello, world"` - строковый литерал
- `'a'` - символьный литерал (=число)
- `; comment` - комментарий

# Организация памяти

1. Память команд. Машинное слово - 32 бит. Реализуется списком словарей, описывающих инструкции (одно слово - одна ячейка). Размер адресного пространства - 2^24 слов.
2. Память данных. Машинное слово - 32 бит, знаковое. Линейное адресное пространство. Реализуется списком чисел. Размер адресного пространства - 2^24 слов.

## Литералы
- строковые - сама строка помещается в статическую память, в месте использования литерала заменяется на адрес расположения строки;
- символьные - по организации в памяти аналогичны числовым литералам, по сути - являются макросом, чтобы не писать каждый раз ASCII код;
- числовые - так как вся работа идет со стеком, то при "вычислении" такого литерального выражения, на стек помещается непосредственно само число, 
значение числа размещается в статической памяти.

## Регистры

- `AC` (Accumulator) - аккумулятор
- `CR` (Command Register) - используется для хранения текущей исполняемой инструкции
- `IP` (Instruction Pointer) - регистр инструкций
- `DR` (Data Register) - регистр данных (для работы с памятью и с вводом/выводом)
- `AR` (Address Register) - адресный регистр (используется при чтении/записи в память)
- `SP` (Stack Pointer) - указатель стека
- `FP` (Frame Pointer) - указатель фрейма
- `BR` (Buffer Pointer) - используется во время выполнения промежуточных операций, чтобы не сбрасывать значение аккумулятора

## Виды Адресации

- `Absolute` - абсолютная, указывается адрес, где находится значение: `value = MEM[address]`
- `Relative` - относительная, указывается регистр и смещение `value = MEM[register + offset]`
- `Relative Inderect` - косвенная относительная, указывается регистр и смещение: `value = MEM[MEM[register + offset]]`

В качестве регистра можно указывать `Stack Pointer` и `Frame Pointer`.
Относительная адресация используется для работы со стеком и локальными переменными функций.

Всего 19 команд, поэтому код инструкции имеет размер 5 бит (32 = 2 ^ 5).
Также, так как видов адресации - 3, то на их кодирование требуется еще 2 бита. 
И 1 бит необходим для кодирования регистра при относительной адресации.
Остается 24 бита. Из-за этого адресное пространство ограничивается 24 битами, 
поэтому память данных также ограничена: ее максимальный объем - 16777216 слов размером 32 бита.

Схема адресных команд:

| Вид Адресации       | Схема                                                  |
|---------------------|--------------------------------------------------------|
| `Relative`          | `[OPCODE: 5][ADDRESSING: 2][REGISTER: 1][OFFSET: 24]`  |
| `Relative Inderect` | `[OPCODE: 5][ADDRESSING: 2][REGISTER: 1][OFFSET: 24]`  |
| `Absolute`          | `[OPCODE: 5][ADDRESSING: 2][RESERVED: 1][ADDRESS: 24]` |

REGISTER: `0` - `Stack Pointer`, `1` - `Stack Frame`

## Система Команд Процессора

### Набор инструкций

```text
add A   - AC + MEM[A] -> AC
sub A   - AC - MEM[A] -> AC
mod A   - AC % MEM[A] -> AC
and A   - AC & MEM[A] -> AC
or A    - AC | MEM[A] -> AC
not     - ~AC -> AC

flags   - FL -> AC
ld A    - MEM[A] -> AC
st A    - AC -> MEM[A]
put     - AC -> IO
get     - IO -> AC
push    - SP - 1 -> SP
pop     - SP + 1 -> SP

jmp A   - A -> IR
jz A    - A -> IR, if AC == 0
call A  - ...
ret     - ...

nop     - no action
halt    - stop
```

### Исполнение инструкций
```text
Instruction Fetch:
IMEM[IP] -> CR
IP + 1 -> IP


Operand Fetch (IF CR.OPCODE IN ADDRESS_COMMANDS):
ABSOLUTE ADDRESS:
    CR[8:31]    -> BR
    BR          -> AR
    MEM[AR]     -> DR

RELATIVE (reg):
    CR[8:31]    -> BR
    BR + $reg   -> AR
    MEM[AR]     -> DR
    
RELATIVE INDIRECT:
    CR[8:31]    -> BR
    BR + $reg   -> AR
    MEM[AR]     -> DR
    DR          -> AR
    MEM[AR]     -> DR


Execution:
add, sub, mod, and, or:
    AC + DR -> AC

not:
    ~AC -> AC

jmp:
    DR -> IP

jz:
    DR -> IP, if FLAGS[ZERO] == 1

call:
    DR      -> BR
    IP      -> DR % PUSH IP
    SP      -> AR
    DR      -> MEM[AR]
    SP - 1  -> SP
    FP      -> DR % PUSH FP
    SP      -> AR
    DR      -> MEM[AR]
    SP - 1  -> SP
    BR      -> IP

ret:
    SP + 1  -> SP % POP FP
    SP      -> AR
    MEM[AR] -> DR
    DR      -> FP
    SP + 1  -> SP % POP IP
    SP      -> AR
    MEM[AR] -> DR
    DR      -> IP
    
ld:
    DR      -> AR
    MEM[AR] -> DR
    DR      -> AC
    
st:
    DR      -> AR
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

flags:
    FLAGS   -> AC
```

### Кодирование инструкций

- Машинный код сериализуется в список JSON.
- Один элемент списка - одно машинное слово, одна инструкция
- Индекс списка - адрес инструкции, используется при командах перехода

Пример:

```json
[
  {
    "opcode": "ret",
    "debug": "return from function print"
  },
  {
    "opcode": "add",
    "operand": {
      "type": "absolute",
      "address": 42
    },
    "debug": ""
  },
  {
    "opcode": "jz",
    "operand": {
      "type": "relative",
      "register": "sp",
      "offset": 3
    },
    "debug": "loop jump"
  }
]
```

где:
- `opcode` - строка с кодом операции
- `operand` - для команд с операндом
- `debug` - дополнительная информация для дебага, не используется при исполнении инструкции

Типы данных описаны в [isa](isa.py), где:
- `Opcode` - перечисление кодов операций;
- `Addressing` - перечисление типов адресации
- `Register` - перечисление регистров, используемых для относительной адресации
