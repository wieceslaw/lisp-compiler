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

1. Память команд. Машинное слово - не определено? TODO
2. Память данных. Машинное слово - 32 бит, знаковое. Линейное адресное пространство. Реализуется списком чисел.

Литералы:
- строковые - сама строка помещается в статическую память, в месте использования литерала заменяется на адрес расположения строки;
- символьные - по организации в памяти аналогичны числовым литералам, по сути - являются макросом, чтобы не писать каждый раз ASCII код;
- числовые - так как вся работа идет со стеком, то при "вычислении" такого литерального выражения, на стек помещается непосредственно само число.

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
- `Immediate` - непосредственная, указывается непосредственное значение: `value = value`

В качестве регистра можно указывать `Stack Pointer` и `Frame Pointer`.
Относительная адресация используется для работы со стеком и локальными переменными функций.

Всего 19 команд, поэтому 32 = 2 ^ 5, т.е. размер кода инструкции размером 5 бит.
Также, так как видов адресации - 4, то на их кодирование требуется еще 2 бита.
Остается 25 бит. Адресные команды принимают адрес, смещение или непосредственное значение в качестве параметра. 
Так как машинное слово данных размером 32 бита, как и машинное слово инструкций, то 25 бит может не хватить для кодирования адресных команд.
Поэтому адресные команды имеют размер - 2 машинных слова (32x2).

Схема адресных команд:

| Вид Адресации       | Схема                                                                |
|---------------------|----------------------------------------------------------------------|
| `Absolute`          | `[OPCODE: 5][ADDRESSING: 2][RESERVED: 25]:[ADDRESS: 32]`             |
| `Immediate`         | `[OPCODE: 5][ADDRESSING: 2][RESERVED: 25]:[VALUE: 32]`               |
| `Relative`          | `[OPCODE: 5][ADDRESSING: 2][REGISTER: 1][RESERVED: 24]:[OFFSET: 32]` |
| `Relative Inderect` | `[OPCODE: 5][ADDRESSING: 2][REGISTER: 1][RESERVED: 24]:[OFFSET: 32]` |

REGISTER: `0` - `Stack Pointer`, `1` - `Stack Frame`

## Система Команд Процессора
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

```text
Работа с данными:
store (address) <value> -> None - записать по адресу значение со стека
load (address) -> <value> - прочитать значение по адресу и положить на стек
put <value> -> None - прочитать значение со стека и записать во вне
get -> <value> - получить слово из вне и положить на стек
push (value) -> <value> - положить литерал на стек
pop -> None - опустить стек

Вычисление:
add <operand> <operand> -> <result> - сложить два числа и положить результат на стек
sub <operand> <operand> -> <result> - вычесть первое число на стеке из второго и положить результат на стек
mod <operand> <operand> -> <result> TODO
and <operand> <operand> -> <result> TODO
or <operand> <operand> -> <result> TODO
not <operand> <operand> -> <result> TODO
sign <operand> <operand> -> <result> TODO

Управление потоком исполнения:
jmp (address) - безусловный переход
jz (address) <value> - переход, если на стеке находится 0 
call (address) - вызов функции, сохраняет адрес возврата и указатель на текущий фрейм
ret - возврат из функции

Остальное:
nop - бездействие, вспомогательная инструкция для упрощения процесса компиляции
halt - остановка 
```

sadd:
ld [sp+1]
add [sp+2]
st [sp]
push

sstore A:
ld [sp+1]
st [A]

sload A:
ld [A]
st [sp+1]
push

sput X:
load #X
put
st [sp+1]
push

sjmp A:
jmp A

sjz A:
load [sp+1]
jz A
