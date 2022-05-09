---
title: expresso.c
subtitle: a recursive descent expression parser in C.
date: 2021-12-25
abstract: I wrote a recursive descent parser in C to evaluate simple expressions.
---

This christmas, I received a copy of Crafting Interpreters.
It inspired me to try to write an interpreter.
But I don't have a ton of time to spend writing a language, so how about something more modest?
Meet expresso.c, my command line calculator program.

Expresso.c is a calculator program that accepts a string like "5\*(3+2)" and returns 25.0.
It supports four binary operations---addition, subtraction, multiplication, and division---as well as the unary negate operator.

![](beans.jpg)

Expresso operates in two phases, tokenization and parsing.
In the first phase, the expression string is converted to a stream of tokens.
In the second phase, the token stream is parsed using a recursive descent parser, and the result is computed.

During the first phase of expresso, the expression string is converted to a token stream.
Tokens represent the fundamental, indivisible pieces of an expression.
In expresso, there are X types of token. One token for each operator, one token for numbers, and one token each for open and cose parens.
The tokenizer consumes characters from the expression string in left-to-right order.
As it processes each new character, the tokenizer decides whether to start a new token or modify the current token.
This is handled by a large switch statement over the current character in the expression string.
As new tokens are produced, they are chained together into a singly linked list.

<aside><p>
  If only I knew what I was doing, this would be a lot better!
</p></aside>

Now that we've tokenized the input string, let's start to build more complex structures out of them.
Backus Normal Form is a nice formalism for representing the atoms and molecules of our arithmetic expressions.
The BNF grammar we will use looks like this:

      #include <stdio.h>

      void main(void) {
        printf("Howdy, doody!\n");
        return 0;
      }

If we apply the BNF grammar to an example expression, we can see the tree-shaped structure that emerges.
At the root, we have the base expression. It is composed of xxx and yyy.
Each sub-expression further decomposes into factors, terms, and numbers.
The second stage of expresso.c walks this tree and computes the final expression result from the bottom up using an algorithm called recursive descent parsing.

    import numpy as np

    def main():
      print("Hello!\n")

<aside><p>
  What do you mean? This looks cool!
</p></aside>

The second stage of expresso.c is parsing the token stream and computing the result.
For this, I use an algorithm called recursive descent parsing.
Recursive descent encodes the BNF grammar in a pile of mutually recursive functions.
For each entry in the BNF grammar, we will create a function that parses that entry, optionally calling other parsing functions as it does so.

Here is a worked example of expresso.c parsing the expression "10\*(3+2)/7"
The token stream: 10, \*, (, 3, +, 2, ), \/, 7
???

"((", "()", "3+-2", PMDAS, ???

Don't be intimidated by compilers, parsers, etc. 
Recursive descent parsing is a beautiful, amazing idea. It just works!?
Compilers are amazing, and good error handling is hard.
Recommendation for Crafting Interpreters.

## Outline

1. Intro
    - This christmas, I received a copy of Crafting Interpreters.
    - It inspired me to try to write an interpreter.
    - But I don't have a ton of time to spend writing a language, so how about something more modest?
    - Meet expresso.c, my command line calculator program.

2. What is the goal?
    - Expresso.c is a calculator program that accepts a string like "5\*(3+2)" and returns 25.0.
    - It supports four binary operations--addition, subtraction, multiplication, and division--as well as the unary negate operator.

3. How does this work?
    - Expresso operates in two phases, tokenization and parsing.
    - In the first phase, the expression string is converted to a stream of tokens.
    - In the second phase, the token stream is parsed using a recursive descent parser, and the result is computed.

4. Tokenizing.
    - During the first phase of expresso, the expression string is converted to a token stream.
    - Tokens represent the fundamental, indivisible pieces of an expression.
    - In expresso, there are X types of token. One token for each operator, one token for numbers, and one token each for open and cose parens.
    - The tokenizer consumes characters from the expression string in left-to-right order.
    - As it processes each new character, the tokenizer decides whether to start a new token or modify the current token.
    - This is handled by a large switch statement over the current character in the expression string.
    - As new tokens are produced, they are chained together into a singly linked list.

<aside><p>
  If only I knew what I was doing, this would be a lot better!
</p></aside>

5. The expresso grammar.
    - Now that we've tokenized the input string, let's start to build more complex structures out of them.
    - Backus Normal Form is a nice formalism for representing the atoms and molecules of our arithmetic expressions.
    - The BNF grammar we will use looks like this: ...

6. The expression tree.
    - If we apply the BNF grammar to an example expression, we can see the tree-shaped structure that emerges.
    - At the root, we have the base expression. It is composed of xxx and yyy.
    - Each sub-expression further decomposes into factors, terms, and numbers.
    - The second stage of expresso.c walks this tree and computes the final expression result from the bottom up using an algorithm called recursive descent parsing.

<aside><p>
  What do you mean? This looks cool!
</p></aside>

7. Recursive descent parsing.
    - The second stage of expresso.c is parsing the token stream and computing the result.
    - For this, I use an algorithm called recursive descent parsing.
    - Recursive descent encodes the BNF grammar in a pile of mutually recursive functions.
    - For each entry in the BNF grammar, we will create a function that parses that entry, optionally calling other parsing functions as it does so.

8. Example expressions?
    - Here is a worked example of expresso.c parsing the expression "10\*(3+2)/7"
    - The token stream: 10, \*, (, 3, +, 2, ), \/, 7
    - ???

9. Testing and Error Handling
    - "((", "()", "3+-2", PMDAS, ???

10. Lessons Learned
    - Don't be intimidated by compilers, parsers, etc. 
    - Recursive descent parsing is a beautiful, amazing idea. It just works!?
    - Compilers are amazing, and good error handling is hard.
    - Recommendation for Crafting Interpreters.
