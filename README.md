Синтаксис:
```ebnf
<program>               := <expressions> EOF

<expressions>           := | <expressions> <expression>

<expression>            := <open-bracket> <bracketed-expression> <close-bracket> | <varname> | <literal>

<bracketed-expression>  :=  <function-definition> 
                            | <function-call> 
                            | <if-condition> 
                            | <binary-operation> 
                            | <assignment> 
                            | <loop-expression>

<function-call>         := <varname> <arguments>

<arguments>             := | <arguments> <expression>

<function-definition>   := defun <varname> <open-bracket> <parameters> <close-bracket> <expressions>

<parameters>            := | <parameters> <varname>

<assignment>            := setq <varname> <expr>

<if-condition>          := if <condition-expression> <true-expression> <false-expression>

<loop-expression>       := loop <condition-expression> <expressions> 

<binary-operator-expression> := <binary-operator> <expression> <expression>

<binary-operator>       := mod | and | or | + | - | * | / | = | < | >

<condition-expression>  := <expression>

<true-expression>       := <expression>

<false-expression>      := <expression>

<literal>               := <number-literal> | <string-literal> | <character-literal>

<number-literal>        := [0-9]+

<string-literal>        := "\w*"

<character-literal>     := '.'

<varname>               := [a-zA-Z]\w*
```

Пример кода:
```lisp
(defun print-str(addr)
    (setq len (load addr))
    (setq i 0)
    (loop (>= len i)
        (setq i (+ i 1))
        (put (load (+ addr i)))
    )
)

(defun is-even (n) 
    (if (= 0 (mod n 2)) 1 0)
)

;; аллоцировать буфер размером 40 слов в статической памяти
;; присвоить адрес выделенной памяти глобальной переменной "buffer"
(setq buffer (alloc 40)) 
;; после компиляции эквивалентно
(setq buffer 0x12345678)
```

Трансляция конструкций в машинный код

Трансляция литералов
```text
% 1
.text
start:
    push 0x1


% "Hello, world!"
.data
$hash: "Hello, world!" % pascal-encoded string

.text
start:
    push $hash
```

Трансляция бинарного оператора
```text
% (+ 1 2) 

.text
start:
    push 1      % 1
    push 2      % 1 2
    add         % 1 2 3
    swop        % 1 3
    swop        % 3
```

Трансляция условного выражения
```text
% (if (= 1 2) 5 20)

.text
start:
    ...
    push 1      % 1
    push 2      % 1 2
    eq          % 1 2 0
    swop        % 1 0
    swop        % 0
    jz   false-$hash
    jnz  true-$hash
true-$hash:
    push 1      
    jmp  after-$hash
false-$hash:
    push 0      % 0 20
    jmp  after-$hash % 0 20
after-$hash:
    swop        % 20
```

Трансляция функций
```text
(defun is-even (n) 
    (= 0 (mod n 2))
)
(defun 5)
% TODO: учесть, что надо pop все выражения в скоупе тела, кроме последнего (результат функции)

.text
is-even-$hash:          % ... 5
    push 0              % ... 5 0
    
    ald 0               % ... 5 0 5
    push 2              % ... 5 0 5 2 
    mod                 % ... 5 0 5 2 1
    % очистка после вызова бинарного оператора
    swop                % ... 5 0 5 1
    swop                % ... 5 0 1
    
    eq                  % ... 5 0 1 0
    % очистка после вызова бинарного оператора
    swop                % ... 5 0 0
    swop                % ... 5 0
    
    % убираем аргументы
    swop                % ... 0
    ret

start:
    % ложим аргументы
    push 5              % 5
    call is-even-$hash  % 5
```

Трансляция директивы setq
```text
(print (defvar i 0))    % становится директивой для выделения статических данных 
(setq i 42)

.data
i$hash: 0

.text
start:
    push    0           % директива раскрывается в Nil (0)
    call    print
    pop                 % так как print в глобальном скопе - подчищаем результат
    
    push    42          % вычисление выражения
    store   [i$hash]    % запись результата по абсолютному адресу глобальной переменной
    pop                 % так как setq вызывается в глобальном скопе - подчищаем результат
```

Трансляция цикла loop
```text
(defvar i 0)
(loop (< i 10)
    (print i)
)

.data
i$hash: 0

.text
start:
    push 0  % директива (defvar i 0) вычисляется в 0
    pop     % очищаем результаты выражения, так как в глобальном скоупе
    
loop$hash:
    % вычисление условного выражения начало
    push    i$hash
    push    10
    less
    swop
    swop
    % вычисление условного выражения конец
    
    jz      after$hash
    
    % тело цикла начало
    push i$hash
    call print
    pop     % очищаем результат, так как скоуп тела цикла
    % тело цикла конец
    
    jmp     loop$hash
    
after$hash:
    pop     % цикл, как выражение, возвращает 0 (после вычисления условного выражения)
            % результат очищаем, так как глобальный скоуп
    halt
```

Инструкции для работы с функциями
```text
*Перед вызовом происходит заполнение стека аргументами функции

call <addr>     % выполнить функцию
    push $sf
    push $ip
    jmp  <addr>
    mov  $fp    % устанавливает stack frame регистр для текущего фрейма

ret % вернуться из функции
    swap        % поменять местами адрес возврата и результат функции
    jmp  $sp    % возврат к предыдущей функции
    pop         % очистить адрес возврата со стека
    swap        % поменять местами стековый фрейм предыдущего вызова и результат функции
    mov  $fp    % загрузить frame pointer предыдущее значение
    pop         % очистить значение со стека 

ald <n> % загрузить n-ую локальную переменную исполняемой функции
    push $fp    % указатель на начало фрейма
    push <n>
    sub
    swop
    swop        % получить адрес n-ой переменной
    load        % получить значение по адресу
    swop        % убрать адрес, оставить значение
    
ast <n> % сохранить значение в n-ую локальную переменную функции
    TODO
```

Трансляция стековых инструкций в 8-битные
```text
push[abs, reg] - загрузить абсолютное значение или из регистра

sub % вычитание двух 32 чисел
    ld  [$sp]       % загрузить первый байт первого операнда
    sub [$sp+4]     % вычесть младший байт второго операнда, положить результат в аккумулятор
    push            % положить результат на стек
    
    ld  [$sp+2]
    sub [$sp+6]
    push
    
    ld  [$sp+4]
    sub [$sp+8]
    push
    
    ld  [$sp+6]
    sub [$sp+12]
    push
    TODO: учесть перенос и так далее

```
TODO: 
- loop evaluation (return value?)
- function declaration + global variable declaration evaluation? + Где можно определять?
- регистры 32 бита
- добавить символьные литералы
