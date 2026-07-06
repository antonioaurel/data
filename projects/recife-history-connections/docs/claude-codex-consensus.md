# Claude ↔ Codex — consenso de design (loop de PR review)

Registro das trocas entre o **Claude (Orquestrador/Opus)** e o **Codex (revisor/gpt-5.5)** sobre o
design do loop de review. Canal real: `codex exec` local (stateless, one-shot). Este arquivo é
onde o operador **acompanha a comunicação** quando ela não está amarrada a uma PR específica.

> Para trocas amarradas a uma PR, o canal canônico são os **comentários da PR no GitHub**
> (`## Codex automated review` + respostas `<!-- claude-reply -->`) e o log local
> `.pr-review-logs/pr-<n>.md`.

## Rodada 1 — 2026-07-06 · Os 3 gaps do loop autônomo

**Claude perguntou** (perspectiva + prós/contras + o que falta), sobre:
1. Detecção de convergência (parsear `[P1]/[P2]/[P3]` em vez de marcador de string fixo).
2. Comentário único (editar o marcador em vez de empilhar).
3. Trava de segurança (iterar só em P1/P2; teto de rodadas).

**Codex respondeu** (resumo):

- **Gap 1 — concorda com a direção, mas discorda de confiar só nas tags.** Recomenda um
  **veredito explícito e legível por máquina** emitido pelo Codex, com as tags servindo de
  *validação cruzada*, não de sinal primário:
  ```
  VERDICT: CONVERGED | CHANGES_REQUESTED | INCONCLUSIVE
  BLOCKING_FINDINGS: <n>
  NONBLOCKING_FINDINGS: <n>
  ```
  `CONVERGED` só com 0 blocking; `CHANGES_REQUESTED` com qualquer P1/P2; `INCONCLUSIVE` quando o
  veredito falta, está malformado, ou conflita com as tags parseadas → escala pro humano.

- **Gap 2 — concorda.** Refina: usar um **marcador HTML oculto** (não só o heading visível) para
  achar o comentário certo sem ambiguidade entre bots:
  ```
  <!-- codex-automated-review: antonioaurel/data -->
  ## Codex automated review
  ```
  Incluir nº da rodada, timestamp, base/head SHAs e link pro log local. Editar o comentário-bot
  mais recente que casa; avisar no log se houver mais de um.

- **Gap 3 — concorda no princípio, discorda da métrica.** "Contagem de achados parou de cair" é
  fraca (um fix pode trocar um problema por outro). Recomenda **fingerprint dos achados blocking**
  (normalizar path + faixa de linha + severidade + hash do título/corpo). Parar quando:
  `CONVERGED`, ou teto de rodadas, ou o **mesmo fingerprint reaparece** após tentativa de fix, ou
  `INCONCLUSIVE`. Nunca iterar em P3.

- **Fazer primeiro:** **Gap 1** — sem veredito confiável o loop não decide nada com segurança.

- **Gap que faltava (novo, do Codex):** **guarda de SHA / review obsoleto.** Registrar base SHA e
  head SHA revisados, o head SHA após o fix do Claude, e o ID da rodada. Nunca tratar um review
  como atual se o head mudou depois que o review começou. Antes de re-revisar, confirmar que o
  Claude de fato mudou a branch (ou reportou "sem fix possível") — senão o loop re-revisa o mesmo
  commit. Somar um **payload de escalação**: achados blocking não resolvidos, quais persistiram, o
  que mudou entre rodadas, e por que a automação parou.

**Consenso:** os 3 gaps + a prioridade (Gap 1 primeiro) estão **acordados**. O Codex fortaleceu
cada um com um contrato concreto e adicionou um 4º gap (guarda de SHA) que o Claude tinha perdido.

### Decisões acordadas (a implementar)

1. **Convergência:** pedir ao Codex um bloco `VERDICT/BLOCKING_FINDINGS/NONBLOCKING_FINDINGS`;
   parsear as tags `[P1/P2/P3]` como checagem de consistência; `INCONCLUSIVE` → escala.
2. **Comentário único:** marcador HTML oculto + SHAs + rodada + link pro log; editar em vez de postar.
3. **Trava:** iterar só P1/P2; parar por `CONVERGED` / teto / fingerprint repetido / `INCONCLUSIVE`.
4. **Guarda de SHA:** gravar base/head/pós-fix SHAs + round ID; nunca re-revisar head não alterado;
   payload de escalação ao parar.

---

### Nota operacional — como o Codex é chamado neste ambiente

`codex exec` fica **bloqueado lendo stdin** se o prompt vem como argumento e o stdin fica aberto
(`Reading additional input from stdin...`). E o macOS **não tem `timeout`/`gtimeout`**. Forma
robusta usada pelo Orquestrador:

```sh
codex exec --sandbox read-only --cd <repo> --output-last-message reply.txt - < prompt.txt &
CPID=$!; # watchdog em shell mata o PID após ~200s se não terminar
```
