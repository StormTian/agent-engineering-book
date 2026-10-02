# Agent 工程拆解

第一版 · 2026-10-02 · 十二案例、十章工程主线。

方法参考：https://github.com/bojieli/ai-agent-book 。正文、案例与练习独立撰写。

证据边界：源码观察、研究推断、独立模型与真实框架运行分别记录。新增四项目未运行真实模型或外部服务。

## 导读

### 回答生成之后，任务才刚开始

模型返回一段文字之后，程序还要判断：动作是否获准，执行结果属于哪次调用，页面变化后旧动作能否继续，重启后应采用哪份状态。本书沿固定版本的源码追踪这些问题，帮助你解释任务如何执行、失败和恢复。

十章主线介绍工程概念，十二个案例提供具体源码路径。你可以先读相关主线，再进入案例；原八份学习包的 52 章交互课程也可继续使用。新增四个案例补充执行交接、代码动作、长期记忆和浏览器行动。全书 179 个概念均有固定版本源码和预测题。

目标与输入 → 上下文装配 → 模型提案 → 工具与执行 → 观察与状态 → 终态与评测

### 怎样使用这本书

先选一个具体问题，例如“重复事件为什么把完成状态改回运行中”。读主线认识术语和责任，进入案例定位源码；写下状态预测后，再展开参考答案。最后换一个输入，检验自己的解释是否仍成立。

有 Go 背景可以先读 Eino；想理解编码 Agent 可从 mini-SWE-agent 与 Pi 开始；关注记忆则从第 2、5 章进入 Letta Code；要建立评测从第 7 章和 Inspect AI 开始。

| 你想解决的问题 | 先读主线 | 再看案例 |
| --- | --- | --- |
| 一次任务如何跑完 | 01 / 03 | mini-SWE-agent、smolagents、Agents SDK |
| 长任务为何丢上下文 | 02 / 05 / 06 | Pi、Codex、Letta Code |
| 并发与恢复如何正确 | 04 / 06 | LangGraph、Eino、OpenHands、DeerFlow |
| 怎样证明任务完成 | 07 / 08 | Inspect AI、browser-use |

### 这本书的证据边界

源码观察给出局部结构与分支；跨项目比较是本书的研究判断；教学模型只验证明确建模的契约。原 Eino 的六案例使用真实框架与脚本模型；新增四项目没有执行真实模型、Cloud 或浏览器任务。每个案例单独列出排除范围。

本书借鉴李博杰《深入理解 AI Agent》以工程问题组织学习的思路，正文、案例编排与练习独立撰写。引用框架源码时保留版本、连续行号和许可；不以仓库星数替代研究价值。

### 先从一条路径读起

第一次阅读可以从第 1 章和 mini-SWE-agent 开始。每章开头给出阅读任务与判断标准；先写预测，再核对源码。读完后合上正文，画出模型、环境、消息和终态之间的关系，并用一个失败样例解释观察怎样回到下一轮输入。

## 01 · 一次任务如何变成执行循环

先区分任务、模型轮次、工具动作与终态。

### 本章阅读任务

追踪一项任务从输入到结束的过程，说明每一轮由模型、工具和运行时分别负责什么。

读前准备：知道函数调用有输入、返回值和异常即可。Runtime 指组织模型调用、工具执行与状态变化的运行时。

1. 用本章的资料比较任务列出允许动作和完成条件。
2. 沿教学循环标出模型输出、动作解释、执行结果与状态记录。
3. 分别预测正常完成、等待审批和预算耗尽时循环在哪里停下。

检验理解：合上正文，画出一轮执行，并说明工具成功后为何仍可能无法完成任务。

判断标准：图中应有输入装配、模型输出、动作解释、执行观察和终止判断；任务验收与工具返回状态分别说明。

### 从一个可验收的输入开始

以一项资料比较任务为例：读取三份已授权的公开资料，比较结论，保存一份带来源的报告。程序需要把用户目标拆成可检查的条件：读哪些资料、允许做什么、保存在哪里、时间预算是多少、什么结果算完成。角色提示词能说明身份，却没有定义这些执行条件。

模型每次返回的是一轮输出，可能包含答案、工具请求、交接请求，也可能格式无效。Runtime（运行时）解释输出，检查并执行允许的动作，接收实际结果，更新状态，再决定下一步。读源码时先追这条循环，再看模型适配和界面。

用户目标与限制 → 装配模型输入 → 模型提出动作或答案 → 运行时检查与执行 → 保存观察和状态 → 继续 / 等待 / 完成 / 失败

### 最小循环的四个责任

最小循环要完成四件事：装配本轮模型输入，解释模型输出，执行动作并收集观察，判断是否结束。它们可以写在一个文件里，也可以由多个服务承担；阅读时要找到每项责任的实际位置。

先用 mini-SWE-agent 追一条线性循环，再看 smolagents 如何把代码作为动作，最后看 OpenAI Agents SDK 如何区分最终输出、交接、审批中断与继续。三者都组织任务执行，但下一步的状态和控制规则各有差异。

本书教学伪代码；不是任何框架的完整实现

```python
while budget.allows_next_turn():
    proposal = model(context.project(state))
    decision = interpret(proposal)
    if decision.kind == "final":
        return validate_and_finish(decision)
    if decision.kind == "wait":
        return checkpoint_and_pause(decision)
    observation = execute_allowed(decision)
    state.record(proposal, observation)
return finish_with_reason("budget_exceeded")
```

### 终止原因要与答案正确性分开

记录终态时，要区分正常结束、预算耗尽、用户停止、等待审批和执行异常。一个 success 布尔值很难交代这些原因。预算耗尽后仍可能有解释文字；工具成功后也可能还有工作未完成。smolagents 的兜底答案和 browser-use 的 done / success 结构提供了具体例子。

跨项目比较前，先写清计数单位：run 通常表示整个任务，turn 常指一次模型调用，step 由各框架定义。一次 browser step 可能包含多个动作，一个 LangGraph superstep 也可能调度多个节点。没有这些定义，“平均十步完成”就无法比较。

| 观察 | 能说明什么 | 仍不能说明什么 |
| --- | --- | --- |
| 模型返回文本 | 收到一个输出 | 任务验收通过 |
| 工具返回无错误 | 本次动作未报告错误 | 外部副作用仅发生一次 |
| 运行退出 | 循环进入了一个终态 | 答案正确且完整 |

### 本章自测

预测：工具执行成功以后，下一轮一定发生吗？

参考：不一定。还要看终止标志、预算、停止与异常处理；观察也可能被直接用于终态。

预测：你应该在哪里记录预算耗尽？

参考：记录在运行终止原因和轨迹中，同时保留已完成动作；不要只展示兜底答案。

## 02 · 上下文是投影，不是全部历史

用三个集合理解长任务：记录、工作状态与模型窗口。

### 本章阅读任务

分清磁盘记录、当前工作状态和模型本轮输入，定位信息在哪一层被遗漏。

读前准备：先理解第 1 章的执行循环。投影是从已有记录中选择、组织本轮所需输入的过程。

1. 把同一任务的完整记录、待办状态和模型窗口分别画出来。
2. 追踪工具调用身份、活动分支和最新用户纠正如何进入窗口。
3. 为压缩后的恢复列出必须保留的字段，再检查失败样例。

检验理解：日志里有一条限制，但模型没有遵守。你会按什么顺序排查？

判断标准：先确认限制是否属于当前分支和任务，再检查状态与最终请求；不能只凭日志存在判断模型已经收到。

### 记录了什么，与模型看到了什么

长任务至少涉及三份信息：完整事件或消息记录、当前工作状态、即将发送给模型的窗口。工作状态可能保存待办、制品路径和审批结果；模型窗口可能只包含当前分支及摘要。排查丢失信息时，要分别检查这三层，不能只看一个名为 history 的变量。

Pi 先确定会话树的活动 leaf，再沿 parentId 选择路径；Codex 压缩专题追踪 replacement history 与之后追加的 suffix；DeerFlow 将摘要、任务状态和制品放在不同字段中。读这些源码时，始终核对记录中有什么，以及本轮请求实际选用了什么。

### 给消息和窗口保留身份

工具结果需要对应原工具调用；压缩后的窗口需要说明替换了哪段输入；新的用户纠正需要保留比旧结论更新的时点。只拼接字符串容易混淆这些关系：旧摘要可能覆盖新值，不同 run 中的同名工具结果也可能配错。

可以按任务列一张检查表：用户限制是否保留，最新纠正是否生效，未完成工具调用是否成对，来源与制品路径能否恢复，终止和等待状态是否清楚。每项都有可检查的对象，也能帮助定位摘要遗漏了什么。

| 层 | 建议检查 | 案例入口 |
| --- | --- | --- |
| 记录层 | 事件身份、父子关系、追加顺序 | Pi / OpenHands |
| 状态层 | 待办、批准调用、制品、当前 Agent | DeerFlow / Agents SDK |
| 模型窗口 | replacement、suffix、输入投影 | Codex / Letta Code |

### 压缩会丢信息，所以要定义保真目标

检验压缩时，先固定任务和必须保留的字段，再加入干扰信息与后来的纠正。比较压缩前后能否恢复正确值、来源和下一步。摘要长度和语言是否流畅可以记录，但不能代替这些保真检查。

恢复前还要核对窗口身份。过期分支的摘要即使语气确定，也不能直接覆盖当前分支状态。本书建议按身份和时点选择权威记录；这是跨项目的工程判断，需要在选定框架中另行验证。

原 Codex 课程中的历史重放、独立教学模型与 fresh runtime 属于不同证据。本书沿用原来的范围：页面构建成功只说明教材可生成，历史兼容阻塞也仍然保留。

### 本章自测

预测：完整日志还在磁盘上，为什么 Agent 仍可能忘记限制？

参考：限制可能未进入活动分支或本轮模型窗口；需要检查投影，而不只检查日志存在。

预测：如何判断一个压缩摘要是否合格？

参考：按冻结的任务必要字段、纠正优先级和下一步恢复条件验收，并保留失败样例。

## 03 · 工具调用是一份可执行契约

参数、调用身份、许可和执行结果缺一不可。

### 本章阅读任务

沿一次工具请求检查参数、调用身份、授权和实际结果，判断失败后能否重试。

读前准备：先理解第 1 章的动作与观察。schema 描述参数形状；call_id 标识某次调用，还需结合运行作用域。

1. 从工具描述追到注册表、参数检查和实际执行器。
2. 将一次调用与对应结果配对，记录许可及失败类型。
3. 预测外部写入完成、回执丢失后再次执行会有什么后果。

检验理解：工具响应丢失时，怎样判断应该查询状态、重试还是停止？

判断标准：区分明确失败和结果未知；保留调用身份，并说明外部状态查询或业务幂等为什么必要。

### 先看 schema，再找实际执行器

从工具描述开始，沿注册表追到执行器，再检查错误如何返回。描述告诉模型可以提出什么请求；执行器把请求交给真实代码或外部系统。工具出现在 schema 里，还需要核对当前用户的许可和服务连接条件。

Eino 案例从 Go 工具接口和参数适配读起；OpenHands 追动作事件与观察的配对；OpenAI Agents SDK 区分启用、guardrail 与审批；mini-SWE-agent 则直接展示命令解析和环境执行。可以用这些入口对照一次请求经过的检查。

### 一个调用名字不够用

tool name 标识一种能力，call_id 标识某次调用。多个运行可能出现同名工具，甚至重复的 call_id，所以配对和去重还需要 run、事件或任务的作用域。DeerFlow 的工具账本案例展示了这个问题。

结果应交代状态、输出和失败类型。拒绝、参数无效、服务不可达、执行失败与结果未知需要不同处理。只返回“失败”会让模型无法判断该改参数、申请授权、重试还是停止。

| 对象 | 核心问题 |
| --- | --- |
| tool name | 这是什么能力？ |
| call id + run scope | 这是哪一次提案？ |
| validated arguments | 真正准备执行什么？ |
| approval / policy decision | 这次调用是否获准？ |
| observation / receipt | 实际发生了什么，有何证据？ |

### 失败后的重试需要业务依据

读操作的重试通常较容易处理，外部写入则需要先确认结果。写入完成而回执丢失时，客户端无法仅靠超时判断是否执行；再试一次可能产生重复记录。此时应保留“结果未知”，查询外部状态或使用业务幂等键。

checkpoint 和事件日志能帮助重建本地决定。要保证外部副作用只发生一次，还需检验执行器、服务端幂等和本地提交之间的故障窗口。本书的独立模拟结果没有被扩展为生产写入保证。

### 本章自测

预测：tool schema 声明了写文件，能证明当前路径已被授权吗？

参考：不能。schema、参数检查、路径许可和宿主隔离承担不同责任。

预测：工具响应丢失后，怎样避免盲目重复写入？

参考：保留调用身份，检查外部实际状态，使用业务幂等或补偿机制，并将结果未知单独表示。

## 04 · 从线性循环走向图与交接

并发、状态合并和控制权转移分别解决不同问题。

### 本章阅读任务

说明图中的依赖、状态合并和控制权交接，预测多个参与者完成工作后谁继续负责。

读前准备：理解执行循环和工具结果。reducer 是合并状态更新的规则；handoff 是把后续控制权交给另一个 Agent。

1. 画出两个节点读取旧状态、写入更新，再由下一节点读取的路径。
2. 分别预测替换、追加和按 ID 合并的结果。
3. 对比专家作为工具和 handoff 后的输入、预算与终止责任。

检验理解：两个节点同时写入消息列表，下一步能看到哪些消息？

判断标准：答案应引用具体的合并规则和可见性边界；不能只根据节点数量或并发方式推断结果。

### 为什么需要图

订单任务先查询订单，再按类型进入物流或退款路径。显式图能把这些依赖写出来：节点完成一块工作，边规定后续关系，reducer 规定多个状态更新怎样合并。读图框架时，先分别找到这三项规则。

LangGraph 的 superstep 规定了本步写入与下一步读取的可见性边界。Eino 的类型图先检查组件输入输出能否连接，再构建执行对象。图中有节点调用模型，仍需另外检查应用怎样组织聊天 Agent。

### 合并规则比节点数量更重要

两个节点同时写消息列表，后续可能看到替换、追加或按 ID 合并的结果。相同 ID 也可能表示修订。需要先读合并契约：简单 append 可能把重试结果加入两次，last value 则可能覆盖另一条必要信息。

可以先画三个节点：A 和 B 读取同一初始状态，各写一条记录，C 在下一步读取。写出 C 会看到什么，再核对 reducer 和调度器。这个小例子能检验状态可见性，也便于追踪预测与源码的差异。

### Agent 作为工具，与 handoff 不同

把专家作为工具时，主持 Agent 等待结果，并继续负责最终答案；handoff 会将后续控制权交给接收 Agent。对照 DeerFlow 的主/子 Agent 委派与 Agents SDK 的 current_agent 切换时，要说明工作结果返回给谁，以及谁决定任务结束。

多个 Agent 可以串行交接，也可以并行处理独立任务。并发只改变执行方式，质量还取决于分工和结果使用；共享状态冲突、工具许可与预算也可能增加。先列出每个参与者的输入、输出、预算和终止责任，再选择编排方式。

| 形式 | 主要价值 | 先验证的失败 |
| --- | --- | --- |
| 线性循环 | 责任集中，容易追踪 | 超限与错误重试 |
| 显式状态图 | 依赖与合并可见 | 并发写入与节点重入 |
| 专家工具 | 分工后由主持者综合 | 专家失败和预算传播 |
| 交接 | 更换当前责任者 | 输入过滤与输出契约变化 |

### 本章自测

预测：两个节点同时写同一个列表，默认一定全部保留吗？

参考：不能默认。需要查看对应 channel / reducer 的实际合并契约。

预测：handoff 后原 Agent 必然回来总结吗？

参考：不必然。交接改变当前 Agent；若希望返回主持者，应明确采用专家工具或设计后续交接。

## 05 · 长期记忆需要写入、检索和更新规则

保存一段文字只是开始。

### 本章阅读任务

为长期记忆设计来源、身份和更新规则，分辨保存、检索与正确使用三个环节。

读前准备：先理解第 2 章的模型窗口。长期记忆跨任务保留信息，工作状态服务当前任务，两者的生命周期不同。

1. 将偏好、临时假设、外部资料与工具许可分开归类。
2. 为一条记忆标出所属对象、来源、日期与失效条件。
3. 预测旧事实被纠正后，新会话应检索和使用哪条记录。

检验理解：怎样区分没有检索到、检索错了和模型使用错了？

判断标准：分别检查存储内容、检索结果和最终输入/输出；文件写入成功不能单独证明持续学习。

### 按生命周期分清三类信息

会话工作状态支持当前任务继续，长期记忆跨任务保存偏好、经验或事实，外部知识库保存有来源的资料。它们都可能进入模型窗口，但有效期、权限和更新方式不同。临时推断需要保留标签，不能悄悄成为永久事实。

Letta Code 案例先确认 Agent 身份和 backend，再解析记忆目录与格式，最后检查投影路径和写入范围。沿这些函数可以解释记忆怎样组织；项目说明中的“Agent 会学习”还需要实际效果实验支持。

### 写入前先问四个问题

写入一条记忆前，先确定所属用户或 Agent、信息类别、来源和时间，以及冲突更新规则。否则旧判断和错误记录可能在后续任务中反复出现，模型也难以判断哪条更可信。

重要记录应保留稳定身份、来源、观察日期和失效条件。纠正旧结论时，明确当前有效值并保留更新历史，避免只把两条相反结论并排追加。本机个人信息、密钥和授权记录另设保存边界；可检索的文字不能自动成为操作许可。

| 记录 | 建议处理 |
| --- | --- |
| 稳定偏好 | 保留来源和更改时间 |
| 临时假设 | 明确标签与复核触发器 |
| 已经失效的结论 | 保存更新历史，当前入口标明失效 |
| 工具许可 | 由权限系统管理，不能靠记忆文字授予 |

### 可检索不等于每次都会被读到

检查记忆可见性时，分别追存储、检索筛选、提示编译和最终请求。Letta 的投影函数只判断路径是否符合条件，仍需检查正文怎样进入模型窗口。研究 Mem0 等候选时，也应分别读 add / update / delete / search。

可以设计一个跨任务实验：写入正确事实，加入干扰，纠正旧值，再在新会话查询。分别保存未检索、检索错误和使用错误的样例，才能判断问题位于存储、检索还是模型解释。

### 本章自测

预测：把总结写入文件，是否已证明持续学习？

参考：没有。还需证明正确接受、下次装配、冲突更新和任务效果改善。

预测：旧记忆说一个事实，新来源纠正它，应如何处理？

参考：保留来源与时点，更新当前权威记录并明确旧值失效，验证后续检索采用新值。

## 06 · 恢复需要一个明确的提交边界

重新连接、重放和继续执行不是同一个动作。

### 本章阅读任务

指出恢复使用的身份与提交边界，判断哪些动作可以继续、哪些结果仍未知。

读前准备：先理解第 2、3 章。checkpoint 是用于继续执行的状态记录；cursor 标识事件流中的读取位置。

1. 区分界面重连、事件回放、进程恢复和审批后继续。
2. 在工具执行、观察保存和状态提交之间选择一个故障点。
3. 预测重启后的下一步，并检查重复副作用和版本兼容问题。

检验理解：工具已经写入外部系统，观察尚未保存时进程退出，恢复需要检查什么？

判断标准：说明原调用身份、外部实际结果和本地提交状态；checkpoint 或完整回放都不能单独保证只写一次。

### 先问你恢复的是什么

界面重连可能只是重新读取事件；进程恢复需要重建运行状态；审批后继续还需保留原工具调用身份。看到 resume 接口时，先确认它支持哪一种恢复，以及调用者仍需提供什么。

DeerFlow 用事件游标回放，LangGraph 用 checkpoint 保存图状态，OpenHands 用事件树与 HEAD 选择活动轨迹，Codex 则结合 replacement history 和后续条目重建窗口。比较时要写出各自保存的对象和提交边界。

### 至少记录五个身份

追恢复路径时，至少标出五个坐标：任务/run、会话/thread、状态版本/checkpoint、事件位置/cursor、工具调用/call id。框架命名可以不同，但应能说明恢复对象、起点、已接受动作、未知结果和下一次模型输入。

故障点应选在状态边界，例如工具执行后、结果保存前，或结果保存后、事件发布前。只在任意时刻结束进程再重启，很难解释恢复差异；存在不可逆的外部动作时尤其如此。

输入接纳 → 动作提案 → 工具执行 → 观察持久化 → 状态提交 → 事件发布 → 下一轮输入

### 重入节点要考虑副作用

interrupt 恢复可能从节点开头重新执行。如果前半段已经发送邮件或修改记录，重入可能再次产生副作用。先确认项目的恢复语义，再明确执行边界，增加业务幂等，或在继续前查询外部实际状态。

历史重放能说明保存的轨迹如何重建。要检验当前二进制与配置、服务和状态格式是否兼容，仍需新的运行。修改配置字段或实验配方后，应保留原失败并说明变更，不能继续按原方案报告通过。

### 本章自测

预测：事件回放完整，可以证明工具没有重复执行吗？

参考：不可以。回放是读取已保存事件；工具副作用需要执行和外部状态证据。

预测：checkpoint 文件存在，足以证明 cold resume 吗？

参考：不够。需要新进程实际恢复、核对版本与状态，并观察下一步行为。

## 07 · 把运行成功与任务成功分别计分

可复现的失败比没有口径的排行榜更有用。

### 本章阅读任务

定义任务成功的判据，并用可追溯的分母报告运行、评分和错误。

读前准备：理解第 1 章的终止原因。Solver 执行求解，Scorer 判定结果；运行结束与得分是不同信息。

1. 为查询、编码或浏览器任务选一个可观察的完成条件。
2. 分别记录计划、运行、评分、正确和失败原因。
3. 固定一个故障类，只改变待比较的策略，保留原始失败。

检验理解：本章 10 个计划样例中 8 个运行、6 个评分、4 个正确，应怎样说明结果？

判断标准：保留 10/8/6/4 四个计数；4/6 只代表已评分样例的准确率，还需列出未评分和未运行原因。

### 固定样例、输入与判据

开始评测前，固定任务分布、允许工具、预算、模型和配置，再写成功判据。查询任务核对来源，编码任务核对补丁与测试，浏览器任务核对页面最终状态。模型声称“完成”可以记入轨迹，最终判断还需对应任务证据。

Inspect AI 用 Task、Solver、Scorer 和日志组织执行与评分；mini-SWE-agent 的 trajectory 与 benchmark runner 区分生成预测和真正解决问题。后续候选τ²-bench 能补充工具、Agent、用户和领域环境之间的交互评测。

### 有效分母不能悄悄变化

样例可能正确、错误、未评分、运行失败，或因基础设施不可用而未执行。若排除不可运行样例后只报 accuracy，读者无法知道实际覆盖范围。报告应同时给出计划、运行、评分、正确的计数及失败原因。

独立教学模型便于固定一个状态契约；真实框架配脚本模型检验接口；真实模型检验动作生成；生产任务检验外部环境。每层证据有自己的用途，需要分别运行和记录，不能自动沿用上一层的通过结论。

| 证据层 | 本书对应内容 | 证明范围 |
| --- | --- | --- |
| 静态源码 | 固定提交与逐字锚点 | 结构和局部分支 |
| 独立教学模型 | 附录四个确定性场景 | 教学契约与反例 |
| 真实框架 + 脚本模型 | 原 Eino 六个案例 | 选定框架接口与路径 |
| 真实环境 + 模型 | 新增四项目尚未执行 | 本书不报告运行成功率 |

### 用故障类组织实验

先选一个故障类，例如重复 call id、观察过期、压缩后纠正丢失或恢复时重复写入。固定其他变量，比较正确策略与错误策略，再解释差异。同时更换框架、模型、提示和预算，会使差异难以归因。

每次实验保存输入、预期、观察、版本、运行时间与边界。修复后先复验已失败样例和相关回归，再决定是否扩大样本。失败样例能指出结论何时不成立，应与成功结果一起保留。

### 本章自测

预测：10 个计划样例，8 个运行、6 个评分、4 个正确，怎样报告？

参考：分别报告 10/8/6/4；已评分准确率为 4/6，另列未评分与未运行原因，不能写“成功率 67%”而省略分母。

预测：独立模型通过，可证明某个真实框架无竞态吗？

参考：不能。它仅检验建模的契约，真实并发与执行器需要单独运行。

## 08 · 授权、信任与沙箱各守一道边界

把“可以描述”与“可以执行”分开验证。

### 本章阅读任务

分别检查能力描述、授权、凭据与执行环境，指出每层能够证明的范围。

读前准备：先理解第 3 章的工具契约。权限策略判断是否允许动作，沙箱限制动作对宿主的影响范围。

1. 将工具 schema、审批、路径、凭据和沙箱放到各自层中。
2. 追踪网页或工具结果中的文字如何成为模型输入。
3. 用本章网页夹具预测越界提案，并核对执行层应如何决定。

检验理解：一个项目已经被信任，且命令在容器里运行，可以推出哪些权限结论？

判断标准：应分别检查资源加载、操作许可、挂载、网络与宿主边界；单层通过不足以说明整条链已经验证。

### 一张能力地图

按执行链逐层检查：schema 描述能力，权限策略判断是否允许，路径检查限制对象，凭据确定服务身份，沙箱限制对宿主的影响。一层通过只能支持该层的结论，还需要核对其他层。

Pi 的项目 Trust 参与扩展加载与项目内容信任；Eino 工具接口规定类型；OpenHands Workspace 决定执行环境；Letta 记忆写入检查逻辑路径与真实路径。它们解决的对象不同，应分别追到实际检查和执行位置。

| 层 | 应核对的证据 |
| --- | --- |
| schema | 模型可提出的参数与工具集合 |
| policy / approval | 调用对象、参数与授权粒度 |
| credentials | 服务身份和权限范围 |
| workspace / sandbox | 挂载、网络、资源与宿主边界 |
| receipt / audit | 实际执行结果与来源 |

### 外部内容是数据

网页、工具输出、检索记忆和仓库文件可能包含看似指令的文字。处理这些材料时，要保留数据来源，追踪它们在哪一层被当成操作决定。材料中的文字不能自行授予操作许可、选择凭据或取消用户限制。

用固定网页夹具检验这条边界：正文含有“忽略用户限制”，而用户目标只允许读取标题。记录模型提出什么、策略如何判断、最后实际做了什么。执行层应按用户许可和对象范围决定动作，即使模型提出了越界请求。

### 沙箱实验必须记录环境

解释器阻止未授权导入，能够说明语言级限制。容器隔离和网络隔离还需另外验证；容器也可能挂载敏感目录或采用高权限网络。OpenSandbox 候选用于补充执行基础设施研究，并与 Agent 控制循环分别检查。

本书没有接触真实 Cookie、API Key 或外部写入账户。本章记录源码边界与后续实验设计，模拟允许列表的结果只支持教学契约，不作为真实沙箱安全结论。

### 本章自测

预测：网页说用户已授权，可以作为工具许可吗？

参考：不能。网页是任务数据；许可应来自用户和受信任的权限机制。

预测：容器里运行就一定无法影响宿主吗？

参考：不能如此推导。应检查挂载、权限、网络、执行器和实际限制。

## 09 · 扩展一个子系统之前，先冻结契约

用最小改变回答一个问题。

### 本章阅读任务

选择一个可重建的小机制，冻结输入输出和不变量，再用正例与反例检验改动。

读前准备：先选择前面一章的具体机制。不变量是在允许的状态变化中必须保持的条件。

1. 从工具账本、消息投影、动作批次或评分聚合中选一项。
2. 先写正常、重复、乱序与缺口输入的预期结果。
3. 对照源码实现小模型，新增一个场景并保留相关旧样例。

检验理解：提交一份输入、预期、观察和未验证条件的对照记录。

判断标准：记录应解释核心不变量和失败原因；独立模型结果与真实框架运行分别标注。

### 选择足够小的重建范围

先选一项可说明输入输出的小机制：工具账本、会话分支投影、reducer 或失败预算。读过多个子系统还不足以重建整个产品；缩小边界后，更容易将实现与源码逐项比较。

以工具账本为例，输入是带 run / call 身份的观察，输出是当前调用状态；需要保持的条件是终态不被迟到的 started 事件降级。再列出失败类型和排除范围。本次先排除数据库与真实工具执行，避免把重建扩大为全套运行时。

### 先预测，再实现，再比较

实现前先写正常、重复、乱序和缺口输入的预期状态，再运行并保存观察。出现差异时，回到契约与反例判断：是代码实现错了，还是原先理解有误？直接复制源码会跳过这一步检验。

附录四个确定性实验提供了独立教学模型，没有导入上游库，也不证明真实服务行为。进入真实框架时，应替换对应接口并保存新的运行证据，保留原模型结果的范围。

| 候选重建 | 核心不变量 | 新失败样例 |
| --- | --- | --- |
| 工具账本 | 调用作用域与终态保护 | 相同 call_id 跨 run |
| 消息投影 | 当前分支与纠正优先级 | 过期分支摘要 |
| 动作批次 | 观察变化后停止 | 焦点变化但 URL 不变 |
| 评测聚合 | 有效分母可追溯 | 未评分与基础设施失败 |

### 扩展需要正例与回归

新增工具或改变合并规则前，先定义新场景的判据，并保留相关旧样例。新功能成功出现，只能说明新路径；旧工具身份、错误处理和恢复是否仍成立，需要回归检查。

设计复盘记录方案选择、关键反例、未验证条件和退回原策略的方法。下一次更新需要依靠这些记录复现判断，因此应与实验结果一起保存。

### 本章自测

预测：怎样证明你理解了一个 reducer？

参考：闭卷预测冲突写入的结果，实现小模型，再对照真实 reducer 与固定样例。

预测：增加一个动作后只跑成功样例，缺少什么？

参考：缺少失败、许可、身份、停止与相关旧行为的回归。

## 10 · 把源码阅读变成可迁移能力

学习成果要由解释、预测和反例证明。

### 本章阅读任务

用追踪、预测、反例与迁移检查自己对源码的理解，选择下一条阅读路径。

读前准备：至少读过一个主线章节和一个相关案例；不要求先读完十二个项目。

1. 选择一条具体输入路径，记录角色、调用和状态变化。
2. 不看答案预测一个失败，再核对源码与已有运行证据。
3. 闭卷复述，并在另一个框架中重新检查身份和成功判据。

检验理解：画出一个案例的五个角色与两种失败，再说明迁移时必须重新核对什么。

判断标准：以该项目的实际路径解释入口、模型、动作、状态与终态；迁移时核对步骤口径、合并、恢复、权限和评分。

### 四遍读同一条路径

围绕同一条输入路径读四遍。先标出入口、循环、工具、状态和终态；再逐步记录调用、旧状态、新状态和观察；随后追解析失败、预算耗尽、重复身份和恢复缺口；最后合上源码，画出主线并解释边界。

遇到陌生语言时，先补当前片段需要的语义，例如 Go 的 interface / context、Python 的异步与异常、TypeScript 的判别联合、Rust 的 enum / Result。这样可以继续追踪代码，也避免只凭变量名猜行为。无需为了一个函数先读完语言教材。

### 推荐三条阅读路线

可以按研究问题选一条路线。运行循环：mini-SWE-agent → smolagents → OpenAI Agents SDK → Pi → browser-use。状态与恢复：LangGraph → Eino → OpenHands → DeerFlow → Codex 压缩。长期记忆与评测：Letta Code → Inspect AI → 跨项目比较 → 候选τ²-bench / Mem0。已有 Go 基础可从 Eino 开始。

这些顺序按概念复杂度与边界递进安排，是教学建议。每次读一条主线，写下三项尚不清楚的问题，再在源码中找答案。项目质量和掌握程度不能由阅读顺序或收藏的仓库数量判断。

### 怎样知道自己真的懂了

用实际回答判断理解程度：能定位入口，说明你认识了角色；能预测状态，说明你能够追踪；能解释失败并给反例，说明你开始推理；能实现有边界的模型并迁移场景，才接近可复用的掌握。教材完成和读者掌握需要分别验收。

原八份交互课程保留章节测验、主动回忆和先修回看。主动回忆保存你的暂定回答，没有自动标为“已掌握”。本书自测的参考答案默认折叠，先写预测，再核对源码和答案。

预测：读完一个案例后，请画出五个角色和两种失败。

参考：入口、模型调用、动作解释/执行、状态、终态；失败应来自该项目实际路径，例如超限与审批中断。

预测：换到另一个框架时，哪些不能直接照搬？

参考：step 的口径、状态合并、恢复身份、权限边界、模型窗口和成功判据都应重新核对。

### 如何更新这本书

更新时先固定新提交，检查引用文件差异，再修改受影响的概念和图。新案例要有明确问题、连续源码范围、白话解释、反例、自测和未验证边界；达到这些条件后，才从候选进入详细案例。

网站界面、静态引用、教学实验、真实框架运行和学习效果分别保存证据。发布当前版说明阅读材料已可用，十二个项目的生产部署与真实模型评测仍按各自记录判断。

## mini-SWE-agent · 从最小编码循环开始

从最小编码循环开始

来源：https://github.com/SWE-agent/mini-swe-agent

提交：`04d809ceab9df28f9adaed044884180159172930`；访问：2026-10-02

证据：独立教学模型3组固定正/错误策略对照；不导入上游，不构成生产Runtime验证。

优先关注解析、首行终止、环境子进程与预测/解决率的区别。

排除：真实模型与供应商质量；真实沙箱/鉴权与部署；跨进程持久恢复及外部副作用恰好一次；并发压力与生产竞态；学习者实际作答及掌握度

### 本案例阅读任务

追踪一个编码任务如何经过配置、模型响应、Bash 执行和终止协议，并区分补丁写入与问题解决。

读前准备：第 1、3 章；能阅读 Python 函数和异常。Environment 指实际执行动作的环境接口。

1. 先读入口与配置，列出最终 Agent、Model 和 Environment 组合。
2. 沿 run 和 step 追一轮消息追加，再读解析、执行和终止条件。
3. 检查费用越界、格式错误与空补丁，最后对照批量运行的计数。

检验理解：解释格式错误为何仍可能产生费用，以及预测文件为何不能证明 SWE-bench 已解决。

判断标准：分别给出查询、计费、解析、提交和独立评测的边界；引用本案例的源码范围。

阅读主线：配置进入 Agent / Model / Environment 三个契约，沿模型输出、Bash 执行和 trajectory 追踪终止。

### 命令入口不是循环本体

安装后的 mini 脚本指向 run.mini 的 CLI app。先在入口定位配置和对象构造，再进入选定 Agent 类的 Agent.run，才能找到实际循环；命令入口只提供了起点。

本课固定提交中，交互入口默认的组件组合与裸 DefaultAgent 并不完全相同。阅读示例时应列出最终 model_class、environment_class、agent_class，而不是依靠文件名猜测。

源码观察：白话翻译
        用户敲 mini 或 mini-swe-agent，都会进入 minisweagent.run.mini:app。真正的装配逻辑在 run script，不在安装器里。

`pyproject.toml:89-92`

```
[project.scripts]
mini = "minisweagent.run.mini:app"
mini-swe-agent = "minisweagent.run.mini:app"
mini-extra = "minisweagent.run.utilities.mini_extra:main"
```

预测：安装 mini 后输入任务，哪个位置决定 Agent 行为？

参考：命令入口负责组织配置；工厂解析 agent_class 并实例化，随后该对象的 run/step 决定循环。对照实际最终配置。

### 递归覆盖与未设置值

配置从左到右递归合并，后项覆盖前项；嵌套字段的合并让 CLI 可以只改 cost_limit 而保留模型其他参数。UNSET 表达未提供，不能随意换成 None。

例如文件配置 cost_limit=3，CLI 未传该项应保留 3；显式传 0 则可能表示关闭该限制。缺失、空值和零是三个不同输入，适配器若混为一谈会悄悄改变运行范围。

源码观察：白话翻译
        每个配置字典从左到右叠加；嵌套字典继续逐层合并。CLI 没显式设置的项用 UNSET，因此不会意外抹掉 YAML 中的值。

`src/minisweagent/utils/serialize.py:6-29`

```
def recursive_merge(*dictionaries: dict | None) -> dict:
    """Merge multiple dictionaries recursively.

    Later dictionaries take precedence over earlier ones.
    Nested dictionaries are merged recursively.
    UNSET values are skipped.
    """
    if not dictionaries:
        return {}
    result: dict[str, Any] = {}
    for d in dictionaries:
        if d is None:
            continue
        for key, value in d.items():
            if value is UNSET:
                continue
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = recursive_merge(result[key], value)
            elif isinstance(value, dict):
                # Recursively merge dict values to filter out nested UNSET values
                result[key] = recursive_merge(value)
            else:
                result[key] = value
    return result
```

预测：CLI 没传超时，能把 None 作为覆盖值吗？

参考：不能把未设置等同显式空值。保留 UNSET 语义并验证递归合并；显式0或None是否有效取决于字段契约。

### 构造顺序帮助定位启动失败

入口先获得模型、环境，再实例化 Agent，最后进入任务运行。工厂失败、容器启动失败与模型在循环内失败发生在不同阶段。

诊断应记录最后成功阶段、配置来源与异常，而不是把没有 trajectory 的启动错误误判为 Agent 回答失败。构造不证明工具执行，也不证明环境具有隔离。

源码观察：白话翻译
        没有任务就询问用户；随后依次构造模型、环境和代理。CLI 的默认选择明确是 local 环境与 interactive Agent，而不是裸 DefaultAgent。

`src/minisweagent/run/mini.py:94-105`

```
    if (run_task := config.get("run", {}).get("task", UNSET)) is UNSET:
        console.print("[bold yellow]What do you want to do?")
        run_task = _multiline_prompt()
        console.print("[bold green]Got that, thanks![/bold green]")

    model = get_model(config=config.get("model", {}))
    env = get_environment(config.get("environment", {}), default_type="local")
    agent = get_agent(model, env, config.get("agent", {}), default_type="interactive")
    agent.run(run_task)
    if (output_path := config.get("agent", {}).get("output_path")):
        console.print(f"Saved trajectory to [bold green]'{output_path}'[/bold green]")
    return agent
```

预测：还没有第一条 assistant 消息就报错，先查什么？

参考：先确认配置合并和组件工厂是否完成、环境是否成功构造；再看是否进入 run。不要先把错误归因于模型输出。

### 协议比聊天字符串更宽

Model 协议除了 query，还规定消息格式化、观察格式化、模板和配置。Agent 使用结构化消息集合；替换模型时，需要按这些接口核对输入输出。

替换模型实现时，只适配 query 返回正文往往不够：动作字段、费用字段和观察编码仍须满足循环预期。源码接口是最低可替换契约，质量与供应商兼容要另外实测。

源码观察：白话翻译
        Model 不只“生成文本”。它还负责消息格式、action 解析后的 observation 格式、模板变量与自身配置序列化。

`src/minisweagent/__init__.py:43-58`

```
class Model(Protocol):
    """Protocol for language models."""

    config: Any

    def query(self, messages: list[dict[str, str]], **kwargs) -> dict: ...

    def format_message(self, **kwargs) -> dict: ...

    def format_observation_messages(
        self, message: dict, outputs: list[dict], template_vars: dict | None = None
    ) -> list[dict]: ...

    def get_template_vars(self, **kwargs) -> dict[str, Any]: ...

    def serialize(self) -> dict: ...
```

预测：自定义模型返回一段 bash 文本就能接入吗？

参考：先满足 Model 的方法与消息结构契约，再对照 Agent 使用的动作、费用和观察字段；正文相似不足以证明可替换。

### Environment 是执行接口

Environment.execute 把动作交给运行环境；Agent.run/save 管理任务和轨迹。三个协议分工使模型、策略、执行位置可以独立更换。

接口统一不意味着安全属性统一。Local 与 Docker 都能执行 Bash，但执行位置、文件可见性、进程寿命和隔离能力不同。必须把环境类型列为实验变量。

源码观察：白话翻译
        Environment 的关键动作只有 execute；Agent 的外部入口只有 run 与 save。循环因此不必知道 Docker 命令或模型 SDK。

`src/minisweagent/__init__.py:61-80`

```
class Environment(Protocol):
    """Protocol for execution environments."""

    config: Any

    def execute(self, action: dict, cwd: str = "") -> dict[str, Any]: ...

    def get_template_vars(self, **kwargs) -> dict[str, Any]: ...

    def serialize(self) -> dict: ...


class Agent(Protocol):
    """Protocol for agents."""

    config: Any

    def run(self, task: str, **kwargs) -> dict: ...

    def save(self, path: Path | None, *extra_dicts) -> dict: ...
```

预测：同一 Agent 换 Local 为 Docker，哪些结论不能沿用？

参考：文件与进程边界、环境变量、生命周期和隔离保证需重验；消息循环契约可复用，但环境接口相同不代表安全相同。

### 名称、类别与默认来源

model_name 指具体模型标识，model_class 指适配器实现。工厂还涉及显式参数、配置和环境变量等默认来源；缺失必要名称会在构造阶段失败。

调试“为什么调用了另一供应商”时，冻结最终解析后的配置以及来源优先级。不得把真实密钥写到教程或轨迹摘要；名称足够解释选择，凭据只在运行时读取。

源码观察：白话翻译
        先得到最终模型名，再选择实现类，并可能按模型名补默认配置。显式 model_class 与模型名是两个不同旋钮。

`src/minisweagent/models/__init__.py:45-62`

```
def get_model(input_model_name: str | None = None, config: dict | None = None) -> Model:
    """Get an initialized model object from any kind of user input or settings."""
    resolved_model_name = get_model_name(input_model_name, config)
    if config is None:
        config = {}
    config = copy.deepcopy(config)
    config["model_name"] = resolved_model_name

    model_class = get_model_class(resolved_model_name, config.pop("model_class", ""))

    if (
        any(s in resolved_model_name.lower() for s in ["anthropic", "sonnet", "opus", "claude"])
        and "set_cache_control" not in config
    ):
        # Select cache control for Anthropic models by default
        config["set_cache_control"] = "default_end"

    return model_class(**config)
```

预测：模型名正确却走错适配器，检查哪两个字段？

参考：同时检查 model_name 与 model_class，以及显式参数、配置、环境默认的选择顺序；只看名称不能确认实现。

### 每次 run 的消息起点

run 初始化任务消息，加入 system 与 user 后进入循环。step 把完整历史交给模型，再将 assistant、环境观察依次追加。这个版本的基本路径是线性历史。

追踪一轮应画出查询前的消息长度、返回后新增 assistant、每个动作生成的观察。不要把工具输出当下一条用户输入，也不要从线性历史推导自动分支恢复。

源码观察：白话翻译
        每次运行先清空旧历史并写入两条起始消息。循环中，格式错误可作为反馈继续；控制流异常把自带消息追加；普通异常留现场后再抛出。只有最后一条消息角色是 exit 才停止。

`src/minisweagent/agents/default.py:88-124`

```
    def run(self, task: str = "", **kwargs) -> dict:
        """Run step() until agent is finished. Returns dictionary with exit_status, submission keys."""
        self.extra_template_vars |= {"task": task, **kwargs}
        self.messages = []
        self.add_messages(
            self.model.format_message(role="system", content=self._render_template(self.config.system_template)),
            self.model.format_message(role="user", content=self._render_template(self.config.instance_template)),
        )
        while True:
            try:
                self.step()
                self.n_consecutive_format_errors = 0  # reset on any clean step
            except FormatError as e:
                # The call was billed before parsing failed, so query() never got to charge it.
                self.cost += e.messages[0].get("extra", {}).get("cost", 0.0)
                self.n_consecutive_format_errors += 1
                if 0 < self.config.max_consecutive_format_errors <= self.n_consecutive_format_errors:
                    self.add_messages(
                        *e.messages,
                        {
                            "role": "exit",
                            "content": "RepeatedFormatError",
                            "extra": {"exit_status": "RepeatedFormatError", "submission": ""},
                        },
                    )
                else:
                    self.add_messages(*e.messages)
            except InterruptAgentFlow as e:
                self.add_messages(*e.messages)
            except Exception as e:
                self.handle_uncaught_exception(e)
                raise
            finally:
                self.save(self.config.output_path)
            if self.messages[-1].get("role") == "exit":
                break
        return self.messages[-1].get("extra", {})
```

预测：一轮工具返回后，下次查询只看工具输出吗？

参考：基本循环传入完整消息集合；本轮 assistant 与环境观察追加到历史，下一轮可见此前 system、user 与往返消息。

### 限制在查询边界检查

查询前检查步数、费用和时间，响应回来后才知道本次真实花费并累加。因此费用上限不是供应商调用内部的精确中断预算。

费用接近上限时，一次请求仍可能使累计值越过阈值，下一轮才会阻止继续。报告 cost_limit 时，要同时说明检查发生在查询前，以及真实费用何时累加，不能宣称它绝不会超额。

源码观察：白话翻译
        query() 先检查限制，把完整 messages 交给 Model，再追加 assistant message；execute_actions() 执行其中每个 action，并把格式化 observation 追加回同一列表。

`src/minisweagent/agents/default.py:126-157`

```
    def step(self) -> list[dict]:
        """Query the LM, execute actions."""
        return self.execute_actions(self.query())

    def query(self) -> dict:
        """Query the model and return model messages. Override to add hooks."""
        if 0 < self.config.step_limit <= self.n_calls or 0 < self.config.cost_limit <= self.cost:
            raise LimitsExceeded(
                {
                    "role": "exit",
                    "content": "LimitsExceeded",
                    "extra": {"exit_status": "LimitsExceeded", "submission": ""},
                }
            )
        if 0 < self.config.wall_time_limit_seconds <= int(time.time() - self._start_time):
            raise TimeExceeded(
                {
                    "role": "exit",
                    "content": "TimeExceeded",
                    "extra": {"exit_status": "TimeExceeded", "submission": ""},
                }
            )
        self.n_calls += 1
        message = self.model.query(self.messages)
        self.cost += message.get("extra", {}).get("cost", 0.0)
        self.add_messages(message)
        return message

    def execute_actions(self, message: dict) -> list[dict]:
        """Execute actions in message, add observation messages, return them."""
        outputs = [self.env.execute(action) for action in message.get("extra", {}).get("actions", [])]
        return self.add_messages(*self.model.format_observation_messages(message, outputs, self.get_template_vars()))
```

预测：上限1美元，累计0.99，下一次请求可能超额吗？

参考：可能。检查发生在请求前，费用在响应后加入。应用若要求硬预算，还需更保守的预留、供应商限制或独立控制。

### 格式错误也可能已经花钱

模型响应的解析与计费有关联：无效动作不意味着没有远程调用，费用仍应计入。FormatError 被反馈给模型重试时，历史会记录失败与纠正。

把解析失败丢弃会同时失去成本与故障证据；把原始回复直接执行则越过动作契约。应保留回复、解析原因和累计费用，执行只发生在格式通过之后。

源码观察：白话翻译
        Model adapter 把供应商响应转成统一 message；即使 action 格式解析失败，也先把被计费响应与成本塞进错误消息。成功时同样保存 actions、原响应、成本和时间。

`src/minisweagent/models/litellm_model.py:81-106`

```
    def query(self, messages: list[dict[str, str]], **kwargs) -> dict:
        for attempt in retry(logger=logger, abort_exceptions=self.abort_exceptions):
            with attempt:
                response = self._query(self._prepare_messages_for_api(messages), **kwargs)
        cost_output = self._calculate_cost(response)
        GLOBAL_MODEL_STATS.add(cost_output["cost"])
        # Note: all model.query() implementations must persist the response and cost on FormatError.
        try:
            actions = self._parse_actions(response)
        except FormatError as e:
            e.messages[0]["extra"].update(cost_output)
            try:
                e.messages[0]["extra"]["response"] = response.model_dump(mode="json")
            except Exception:
                # model_dump failed (e.g. unserializable object); fall back to repr
                # so the spec contract ("response MUST be persisted") holds unconditionally.
                e.messages[0]["extra"]["response"] = repr(response)
            raise
        message = response.choices[0].message.model_dump()
        message["extra"] = {
            "actions": actions,
            "response": response.model_dump(),
            **cost_output,
            "timestamp": time.time(),
        }
        return message
```

预测：JSON 动作解析失败，这轮费用能删除吗？

参考：不能仅因格式失败抹掉已发生调用成本。保留响应与 FormatError，按策略反馈重试；环境不能执行未解析通过的动作。

### Schema 与动作解析两道门

工具 schema 告诉模型只调用 bash，参数中 command 必须是字符串；实际解析仍验证工具名、JSON 形状和字段类型。模型看到 schema 不等于永远遵守。

执行应位于解析成功之后。缺字段、错误工具名或损坏 JSON 应走 FormatError，而不是尝试从正文抽取一段看起来像命令的文本。

源码观察：白话翻译
        没有 tool call、工具名不是 bash、JSON 无法解析或缺 command，都会变成可回送模型的 FormatError；通过检查后才产出统一 action 字典。

`src/minisweagent/models/utils/actions_toolcall.py:40-76`

```
    if not tool_calls:
        raise FormatError(
            {
                "role": "user",
                "content": Template(format_error_template, undefined=StrictUndefined).render(
                    error="No tool calls found in the response. Every response MUST include at least one tool call.",
                    actions=[],
                    has_tool_calls=False,
                    **template_kwargs,
                ),
                "extra": {"interrupt_type": "FormatError"},
            }
        )
    actions = []
    for tool_call in tool_calls:
        error_msg = ""
        args = {}
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception as e:
            error_msg = f"Error parsing tool call arguments: {e}."
        if tool_call.function.name != "bash":
            error_msg += f"Unknown tool '{tool_call.function.name}'."
        if not isinstance(args, dict) or "command" not in args:
            error_msg += "Missing 'command' argument in bash tool call."
        if error_msg:
            raise FormatError(
                {
                    "role": "user",
                    "content": Template(format_error_template, undefined=StrictUndefined).render(
                        actions=[], error=error_msg.strip(), has_tool_calls=True, **template_kwargs
                    ),
                    "extra": {"interrupt_type": "FormatError"},
                }
            )
        actions.append({"command": args["command"], "tool_call_id": tool_call.id})
    return actions
```

预测：模型说“已经执行 rm”，如何确认？

参考：检查结构化 tool call 是否通过解析、确认闸门是否允许、环境 execute 是否发生以及对应观察。模型正文不是执行证据。

### 确认模式决定行动许可

InteractiveAgent 可以逐条确认、处理白名单或 yolo 配置。确认失败与格式错误不同：动作可合法却未获执行许可。

一次回复包含多个动作时，已执行观察和后续未执行项必须分清。用户拒绝第二条，不应让下一轮误以为两条都运行；也不应因为“工具可用”自动批准所有命令。

源码观察：白话翻译
        只有 confirm 模式且 action 未匹配白名单时才询问；空输入或 /y 放行，/u 切到 human，其余文字作为拒绝反馈。yolo 会绕过这道人工闸门。

`src/minisweagent/agents/interactive.py:162-182`

```
    def _should_ask_confirmation(self, action: str) -> bool:
        return self.config.mode == "confirm" and not any(re.match(r, action) for r in self.config.whitelist_actions)

    def _ask_confirmation_or_interrupt(self, commands: list[str]) -> None:
        if not any(self._should_ask_confirmation(c) for c in commands):
            return
        prompt = (
            f"[bold yellow]Execute {len(commands)} action(s)?[/] [green][bold]Enter[/] to confirm[/], "
            "[red]type [bold]comment[/] to reject[/], or [blue][bold]/h[/] to show available commands[/]\n"
            "[bold yellow]>[/bold yellow] "
        )
        match user_input := self._prompt_and_handle_slash_commands(prompt).strip():
            case "" | "/y":
                pass  # confirmed, do nothing
            case "/u":  # Skip execution action and get back to query
                self._interrupt("Commands not executed. Switching to human mode", itype="UserRejection")
            case _:
                self._interrupt(
                    f"Commands not executed. The user rejected your commands with the following message: {user_input}",
                    itype="UserRejection",
                )
```

预测：同轮第二个命令被拒绝，下一轮应看见什么？

参考：保留已经执行的输出，并明确后续动作未执行及拒绝原因。能力描述、解析有效与用户许可分别记录。

### 新 subprocess 不保存 shell 状态

Local 环境为动作启动新的进程；cwd 和环境变量来自配置。上一条命令里的 cd 或 export 不会自动成为下一条进程的持久状态。

连续操作需要放在同一次命令中，例如将 cd 与目标命令一起执行，或显式配置 cwd。Local 直接访问主机；超时和进程组清理只能说明进程管理，不能证明沙箱隔离。

源码观察：白话翻译
        每个 action 新建一个 shell 子进程；超时会杀掉进程组并保存已有 stdout。它不是持续 shell，因此上一条命令里的 cd 或临时 export 不会自动留到下一条。

`src/minisweagent/environments/local.py:72-92`

```
def _run(command: str, cwd: str, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    """Like subprocess.run, but kills the whole process group on timeout so no children are orphaned."""
    process = subprocess.Popen(
        command,
        shell=True,
        text=True,
        cwd=cwd,
        env=env,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=os.name == "posix",
    )
    try:
        stdout, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL) if os.name == "posix" else process.kill()
        stdout, _ = process.communicate()
        raise subprocess.TimeoutExpired(command, timeout, output=stdout)
    return subprocess.CompletedProcess(command, process.returncode, stdout=stdout)
```

预测：第一条 cd /tmp，第二条 pwd 会一直在 /tmp 吗？

参考：不能这样假设。两次动作是不同子进程；使用同一命令中的 cd && pwd 或明确设置工作目录，并区分进程管理与隔离。

### 终止协议看第一行和退出码

完成标志是输出协议：返回码为 0，且去除首尾空白后的第一行精确符合 sentinel，后续行才作为提交内容。输出中任意位置出现词语不构成完成。

这避免模型引用说明文本时提前终止。失败命令即使打印了标志也不能正常提交。教学实验故意比较“包含关键词”和精确协议的不同结果。

源码观察：白话翻译
        环境先去掉开头空白，把 stdout 拆成行。首行必须精确匹配 sentinel，且命令成功；后续所有行才成为 submission，并随一条 exit message 抛回 Agent。

`src/minisweagent/environments/local.py:45-56`

```
    def _check_finished(self, output: dict):
        """Raises Submitted if the output indicates task completion."""
        lines = output.get("output", "").lstrip().splitlines(keepends=True)
        if lines and lines[0].strip() == "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT" and output["returncode"] == 0:
            submission = "".join(lines[1:])
            raise Submitted(
                {
                    "role": "exit",
                    "content": submission,
                    "extra": {"exit_status": "Submitted", "submission": submission},
                }
            )
```

预测：日志第三行出现完成标志，可以终止吗？

参考：不行。按当前实现验证返回码和第一行精确匹配，再取后续提交；引用、子串与失败返回码都不能替代协议。

### finally 保存故障现场

循环通过控制流异常表达提交、限制、超时等退出；finally 路径尝试保存轨迹。格式错误可作为可恢复反馈，其计数和最终状态仍应保留。

保存是证据机制，文件存在不等于修复成功。路径没配置或文件写入失败也有边界；报告应区分 Agent 退出原因与轨迹持久化是否完成。

源码观察：白话翻译
        FormatError 有机会成为下一轮反馈，连续过多才转成 exit；其他控制流异常直接追加自带消息。无论哪条路，finally 都先尝试保存轨迹。

`src/minisweagent/agents/default.py:96-124`

```
        while True:
            try:
                self.step()
                self.n_consecutive_format_errors = 0  # reset on any clean step
            except FormatError as e:
                # The call was billed before parsing failed, so query() never got to charge it.
                self.cost += e.messages[0].get("extra", {}).get("cost", 0.0)
                self.n_consecutive_format_errors += 1
                if 0 < self.config.max_consecutive_format_errors <= self.n_consecutive_format_errors:
                    self.add_messages(
                        *e.messages,
                        {
                            "role": "exit",
                            "content": "RepeatedFormatError",
                            "extra": {"exit_status": "RepeatedFormatError", "submission": ""},
                        },
                    )
                else:
                    self.add_messages(*e.messages)
            except InterruptAgentFlow as e:
                self.add_messages(*e.messages)
            except Exception as e:
                self.handle_uncaught_exception(e)
                raise
            finally:
                self.save(self.config.output_path)
            if self.messages[-1].get("role") == "exit":
                break
        return self.messages[-1].get("extra", {})
```

预测：trajectory.json 存在，能说修复成功吗？

参考：不能。核对 exit_status、submission、消息和错误；轨迹保存与任务质量分别验收，真实修复还要独立测试。

### 可读截断与原始输出

长工具输出可在模型可见消息中截断，而额外字段保留 raw_output。两种视图分别服务上下文预算与复盘证据。

工具结果缺少报错时，依次检查进程是否产生输出、输出是否收集成功，以及模型可见文本是否被截断。截断片段不能作为完整命令结果；保存原始输出也要遵守敏感数据边界。

源码观察：白话翻译
        observation 的 content 由模板渲染，默认配置会截短过长输出；消息 extra 另存完整 raw_output、returncode、时间与异常。部分 action 未执行时也有明确占位。

`src/minisweagent/models/utils/actions_toolcall.py:87-104`

```
    """Format execution outputs into tool result messages."""
    not_executed = {"output": "", "returncode": -1, "exception_info": "action was not executed"}
    padded_outputs = outputs + [not_executed] * (len(actions) - len(outputs))
    results = []
    for action, output in zip(actions, padded_outputs):
        content = Template(observation_template, undefined=StrictUndefined).render(
            output=output, **(template_vars or {})
        )
        msg = {
            "content": content,
            "extra": {
                "raw_output": output.get("output", ""),
                "returncode": output.get("returncode"),
                "timestamp": time.time(),
                "exception_info": output.get("exception_info"),
                **output.get("extra", {}),
            },
        }
```

预测：模型没看到堆栈尾部，是否说明进程没有堆栈？

参考：不一定。检查原始输出与格式化截断规则，分别记录执行结果和模型可见内容；保留证据不等于向模型发送全部文本。

### 样本拥有独立运行对象

批量运行器为每个实例组织任务、模型、环境、Agent 和输出文件。配置进度包装器不会改变基类循环，但样本隔离仍依赖对象和环境生命周期。

并发实例不能共享消息历史或随意复用工作目录。静态阅读只能确认构造意图，真实容器隔离、资源回收和压力表现仍未验证。

源码观察：白话翻译
        单例开始时先清理旧预测与旧 trajectory，创建独立 Model 和 Environment，再把 problem statement 交给进度版 DefaultAgent。循环结束后只取 exit status 与 submission。

`src/minisweagent/run/benchmarks/swebench.py:122-156`

```
def process_instance(
    instance: dict,
    output_dir: Path,
    config: dict,
    progress_manager: RunBatchProgressManager,
) -> None:
    """Process a single SWEBench instance."""
    instance_id = instance["instance_id"]
    instance_dir = output_dir / instance_id
    # avoid inconsistent state if something here fails and there's leftover previous files
    remove_from_preds_file(output_dir / "preds.json", instance_id)
    (instance_dir / f"{instance_id}.traj.json").unlink(missing_ok=True)
    model = get_model(config=config.get("model", {}))
    task = instance["problem_statement"]

    progress_manager.on_instance_start(instance_id)
    progress_manager.update_instance_status(instance_id, "Pulling/starting environment")

    agent = None
    exit_status = None
    result = None
    extra_info = {}

    try:
        env = get_sb_environment(config, instance)
        agent = ProgressTrackingAgent(
            model,
            env,
            progress_manager=progress_manager,
            instance_id=instance_id,
            **config.get("agent", {}),
        )
        info = agent.run(task)
        exit_status = info.get("exit_status")
        result = info.get("submission")
```

预测：批量提速时共享一个 Agent 安全吗？

参考：先证明历史、计费、任务状态和环境均不串样本；当前按实例构造的主线不支持直接推导任意共享方案安全。

### 预测写入不是 resolved

预测文件以实例 ID 保存模型名和补丁内容，锁保护读改写过程。该字段没有自动证明补丁通过 SWE-bench 的测试。

异常仍可能留下空提交和失败信息；resume 按已有 ID 跳过时，存在记录也不等于有效结果。应另列运行成功数、有效补丁数与独立评测 resolved 数。

源码观察：白话翻译
        共享 preds.json 用锁保护“读—改—写”，每个 instance 记录模型名、ID 与 model patch。这里没有 score、resolved 或测试结果字段。

`src/minisweagent/run/benchmarks/swebench.py:97-108`

```
def update_preds_file(output_path: Path, instance_id: str, model_name: str, result: str):
    """Update the output JSON file with results from a single instance."""
    with _OUTPUT_FILE_LOCK:
        output_data = {}
        if output_path.exists():
            output_data = json.loads(output_path.read_text())
        output_data[instance_id] = {
            "model_name_or_path": model_name,
            "instance_id": instance_id,
            "model_patch": result,
        }
        output_path.write_text(json.dumps(output_data, indent=2))
```

预测：preds 中有100条记录，就是解决100题吗？

参考：不是。记录可能为空或失败；resolved 必须来自独立评测。分别报告计划、预测、有效补丁和测试通过数。

### 并发取消不是瞬间终止所有任务

线程池提交样本，异常与中断时会处理 future。取消待运行任务和等待已运行任务的结果是不同操作；已经启动的工作不会只因 cancel 请求立刻消失。

设计可恢复批处理时应冻结完成判定、写入原子性和错误策略，再验证中途退出后的重跑。把“文件有键就跳过”当成功标准会将失败固化。

源码观察：白话翻译
        workers 决定线程数；每个 future 对应一个 instance ID。Ctrl-C 只取消尚未开始的任务，正在运行与已完成 future 仍由收尾逻辑处理。

`src/minisweagent/run/benchmarks/swebench.py:245-271`

```
    def process_futures(futures: dict[concurrent.futures.Future, str]):
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except concurrent.futures.CancelledError:
                pass
            except Exception as e:
                instance_id = futures[future]
                logger.error(f"Error in future for instance {instance_id}: {e}", exc_info=True)
                progress_manager.on_uncaught_exception(instance_id, e)

    with Live(progress_manager.render_group, refresh_per_second=4):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(process_instance, instance, output_path, config, progress_manager): instance[
                    "instance_id"
                ]
                for instance in instances
            }
            try:
                process_futures(futures)
            except KeyboardInterrupt:
                logger.info("Cancelling all pending jobs. Press ^C again to exit immediately.")
                for future in futures:
                    if not future.running() and not future.done():
                        future.cancel()
                process_futures(futures)
```

预测：恢复时如何避免空失败结果永久被跳过？

参考：先定义有效完成条件与失败重试策略，核对提交和状态；保留历史错误，明确重跑集合，不能只按记录键存在判定成功。

### 闭卷复述与迁移

解释格式错误为何仍可能产生费用，以及预测文件为何不能证明 SWE-bench 已解决。

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## Pi · 一条终端输入与一棵会话树

一条终端输入与一棵会话树

来源：https://github.com/earendil-works/pi

提交：`36b60d2e8985899743c4cf5bd5f8929832a3f05d`；访问：2026-10-02

证据：独立教学模型3组固定正/错误策略对照；不导入上游，不构成生产Runtime验证。

不要把项目 Trust 写成系统沙箱；steer / follow-up 也需要明确主运行边界。

排除：真实模型与供应商质量；真实沙箱/鉴权与部署；跨进程持久恢复及外部副作用恰好一次；并发压力与生产竞态；学习者实际作答及掌握度

### 本案例阅读任务

从终端输入追到主运行、工具批次和会话树，解释当前分支怎样组成下一次模型输入。

读前准备：第 1、2 章；能阅读 TypeScript 的 async/await 和事件处理。leaf 是当前会话分支的末端。

1. 先追 session.prompt 的调用者和输入预处理顺序。
2. 对比主运行保护、steer/follow-up 和工具批次调度。
3. 沿 parentId 和当前 leaf 重建上下文，再检查压缩与截断调用。

检验理解：保留两个会话分支时，为什么不能把整个 JSONL 按时间顺序直接发给模型？

判断标准：指出物理追加与活动路径的区别，并说明最新压缩条目和有效尾部如何参与输入投影。

阅读主线：从交互输入经过 AgentSession、模型流、工具与会话分支，解释当前路径如何组成上下文。

### 终端入口与串行等待

界面接到输入后，会等待 session.prompt 完成，异常交给 showError 处理。按下 Enter 并不直接调用 Provider；如果界面有输入而模型没有请求，应先检查调用模型之前的阶段。

追踪时分两条路径：新请求进入 prompt，运行中的新输入进入 steer/follow-up。界面允许继续打字，不足以说明两个主运行能同时修改状态。排查时记录输入类型、是否正在流式运行，以及最后成功的阶段。

源码观察：白话翻译
        交互模式持续等待输入。每次拿到一条普通消息，就等待 session.prompt() 完成；若前置检查或运行失败，错误回到界面显示。

`packages/coding-agent/src/modes/interactive/interactive-mode.ts:1136-1145`

```
		// Main interactive loop
		while (true) {
			const userInput = await this.getUserInput();
			try {
				await this.session.prompt(userInput);
			} catch (error: unknown) {
				const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
				this.showError(errorMessage);
			}
		}
```

预测：按 Enter 后没有网络请求，如何定位？

参考：先确认输入是否为扩展命令，再查压缩门禁、输入钩子、模型与认证；只有经过这些阶段才检查 Provider。不能凭输入已显示就判模型失败。

### 预处理顺序的行为含义

输入依次经过扩展命令、压缩状态检查、输入钩子，再展开 Skill 和模板。钩子可能改写或消耗消息，所以顺序会影响后续输入；扩展已完成处理时，也可能无需调用模型。

例如钩子改写命令后，模板展开读取的是新内容；提前展开可能产生不同结果。分析时保留原始输入和最终模型消息，避免把扩展生成的文字归为用户原话。

源码观察：白话翻译
        斜杠命令先尝试由 Extension 接管；压缩进行中会拒绝新主请求；输入钩子可以处理或改写内容；最后才展开 Skill 与 Prompt Template。顺序变化会改变可见行为。

`packages/coding-agent/src/core/agent-session.ts:1255-1291`

```
		try {
			// Handle extension commands first (execute immediately, even during streaming)
			// Extension commands manage their own LLM interaction via pi.sendMessage()
			if (expandPromptTemplates && text.startsWith("/")) {
				const handled = await this._tryExecuteExtensionCommand(text);
				if (handled) {
					// Extension command executed, no prompt to send
					preflightResult?.(true);
					return;
				}
			}

			if (this._compactionAbortController !== undefined) {
				throw new Error(
					"Cannot submit a prompt while compaction is in progress. Wait for compaction to finish and retry.",
				);
			}

			// Emit input event for extension interception (before skill/template expansion)
			const processedInput = await this._runInputHandlers(
				text,
				options?.images,
				options?.source ?? "interactive",
				this.isStreaming ? options?.streamingBehavior : undefined,
			);
			if (!processedInput) {
				preflightResult?.(true);
				return;
			}
			const { text: currentText, images: currentImages } = processedInput;

			// Expand skill commands (/skill:name args) and prompt templates (/template args)
			let expandedText = currentText;
			if (expandPromptTemplates) {
				expandedText = this._expandSkillCommand(expandedText);
				expandedText = expandPromptTemplate(expandedText, [...this.promptTemplates]);
			}
```

预测：修改输入钩子后模板未展开，是不是模板加载失败？

参考：先检查钩子是否将输入标为handled，以及改写后的内容是否仍匹配模板；只有仍需下游处理时再查模板资源。

### 请求拒绝与排队的区别

await 表示这条交互路径正在等待。能否接纳新输入，还取决于 Agent 状态和 Session 预处理；拒绝、排队、改写与执行应分别记录。

消息队列安排输入何时进入循环，不会自动越过压缩或认证检查。读代码时，从 prompt 向上找调用者，向下找 Agent.prompt 的运行保护，分别判断 UI 响应和 Agent 状态的并发约束。

源码观察：白话翻译
        交互模式持续等待输入。每次拿到一条普通消息，就等待 session.prompt() 完成；若前置检查或运行失败，错误回到界面显示。

`packages/coding-agent/src/modes/interactive/interactive-mode.ts:1136-1145`

```
		// Main interactive loop
		while (true) {
			const userInput = await this.getUserInput();
			try {
				await this.session.prompt(userInput);
			} catch (error: unknown) {
				const errorMessage = error instanceof Error ? error.message : "Unknown error occurred";
				this.showError(errorMessage);
			}
		}
```

预测：用户连续输入两次，什么证据能区分拒绝与排队？

参考：读取输入反馈、queue状态和后续消息进入循环的时点；拒绝应有明确错误，排队应有可追踪的队列与消费事件。最终一段文字不够。

### 包边界与修改归属

coding-agent 是产品层，agent 提供可复用循环，ai 适配模型协议，TUI 负责终端界面。这是代码包的职责划分，包名不表示部署服务端口。

工具结果没有回到下一轮，先查 agent 的循环和消息追加；供应商流解析失败，查 ai；终端显示与持久消息不一致，查 coding-agent/TUI。按输入输出定位责任，可以缩小修改范围，也避免界面调整影响循环决策。

源码观察：白话翻译
        coding-agent 是可直接使用的产品层；agent 提供可复用循环；ai 把不同 Provider 统一到共同消息与流接口。改 UI 不应落到 Provider，改工具循环也不该塞进 TUI。

`README.md:13-19`

```
# Pi Agent Harness

This is the home of the Pi agent harness project including our self extensible coding agent.

* **[@earendil-works/pi-coding-agent](packages/coding-agent)**: Interactive coding agent CLI
* **[@earendil-works/pi-agent-core](packages/agent)**: Agent runtime with tool calling and state management
* **[@earendil-works/pi-ai](packages/ai)**: Unified multi-provider LLM API (OpenAI, Anthropic, Google, …)
```

预测：新增一个Provider，应从哪层开始？

参考：从ai的模型与流接口接入，并验证统一消息/事件格式；coding-agent负责选择和配置，Agent Core不应硬编码该供应商。

### 同一运行时的多种入口

默认交互入口创建 InteractiveMode。终端、RPC 和打印模式使用同一运行时的不同呈现方式，阅读时先找到共享的执行路径，再检查各入口的差异。

更换宿主入口时，要保留输入归一化与事件消费契约。取消、流显示和错误反馈可能随入口而变，因此每种入口仍需单独验证；一个 CLI 成功不能替其他传输模式验收。

源码观察：白话翻译
        命令行模式不是不同的 Agent 大脑，而是同一运行时的不同入口。默认交互模式创建 InteractiveMode，并带上诊断、初始消息和界面设置。

`packages/coding-agent/src/main.ts:929-944`

```
	if (appMode === "rpc") {
		printTimings();
		await runRpcMode(runtime);
	} else if (appMode === "interactive") {
		const interactiveMode = new InteractiveMode(runtime, {
			migratedProviders,
			startupDiagnostics,
			modelFallbackMessage,
			autoTrustOnReloadCwd,
			initialMessage,
			initialImages,
			initialMessages: parsed.messages,
			verbose: parsed.verbose,
			tuiMode: parsed.tuiMode,
			initialThemeSetting: parsed.useTheme,
		});
```

预测：把CLI换成网页时，哪些东西可以复用？

参考：循环、消息契约和工具装配可复用；网页连接、身份、事件显示、取消和重连需要应用层设计与验证。

### 注入模型与上下文转换

sdk 将模型、思考配置、消息转换和 stream 函数注入 Agent。依赖注入让循环可以使用替身模型，在不连接真实网络的情况下验证执行路径。

Agent 上下文与 LLM 消息可能并非一一对应，transformContext 和 convertToLlm 会筛选或改写输入。排查模型为何缺少信息时，同时核对持久记录和最终请求，确认信息是否真正传给 Provider。

源码观察：白话翻译
        Coding Agent 把选中的模型、思考级别、消息转换和 Provider 流函数注入通用 Agent。Agent Core 不硬编码某一家模型；真正的网络调用由 modelRuntime.streamSimple 承接。

`packages/coding-agent/src/core/sdk.ts:306-325`

```
	agent = new Agent({
		initialState: {
			systemPrompt: "",
			model,
			thinkingLevel,
			tools: [],
		},
		convertToLlm: convertToLlmWithBlockImages,
		streamFn: async (model, context, options) => {
			const providerRetrySettings = settingsManager.getProviderRetrySettings();
			const httpIdleTimeoutMs = settingsManager.getHttpIdleTimeoutMs();
			// SDKs treat timeout=0 as 0ms (immediate timeout), not "no timeout".
			// Use max int32 to effectively disable the timeout.
			const effectiveTimeoutMs = httpIdleTimeoutMs === 0 ? 2147483647 : httpIdleTimeoutMs;
			const timeoutMs = options?.timeoutMs ?? providerRetrySettings.timeoutMs ?? effectiveTimeoutMs;
			const websocketConnectTimeoutMs =
				options?.websocketConnectTimeoutMs ?? settingsManager.getWebSocketConnectTimeoutMs();
			const headerRunner = extensionRunnerRef.current;
			return modelRuntime.streamSimple(model, context, {
				...options,
```

预测：会话文件有证据，模型仍不知道，应核对什么？

参考：核对有效分支投影、压缩、transformContext和convertToLlm之后的实际消息；不能直接由文件存在推断模型已收到。

### 主运行保护

Agent.prompt 拒绝同时启动第二个主运行，保护当前 Agent 状态。普通文本先规范化，再进入统一路径。

这项保护只约束这里的主运行，不能推出跨进程或跨用户锁，也不能推出全部工具必须串行。分析竞争时分别看主运行、工具批次和输入队列；两个 Agent 实例仍可能访问同一个外部文件。

源码观察：白话翻译
        同一个 Agent 不允许两个主运行同时改状态。新输入要么等待，要么明确进入 steer/follow-up 队列；普通文本先规范化成消息，再进入统一运行路径。

`packages/agent/src/agent.ts:363-374`

```
	/** Start a new prompt from text, a single message, or a batch of messages. */
	async prompt(message: AgentMessage | AgentMessage[]): Promise<void>;
	async prompt(input: string, images?: ImageContent[]): Promise<void>;
	async prompt(input: string | AgentMessage | AgentMessage[], images?: ImageContent[]): Promise<void> {
		if (this.activeRun) {
			throw new Error(
				"Agent is already processing a prompt. Use steer() or followUp() to queue messages, or wait for completion.",
			);
		}
		const messages = this.normalizePromptInput(input, images);
		await this.runPromptMessages(messages);
	}
```

预测：同一个Agent正在工作，直接再调用prompt会怎样？

参考：触发运行保护，不能启动第二条主循环；如要引导或跟进，应使用对应队列与入口，而非绕过状态检查。

### 模型与工具的闭环

模型返回 assistant 消息后，ToolCall 决定是否执行工具。工具结果追加到当前上下文和本轮新增消息，下一次模型生成才能引用实际执行结果。

按 message、tool call、tool result 和下一次请求逐项配对。工具错误也需要形成可理解的结果；模型写“已经测试通过”，仍需对应实际工具输出。

源码观察：白话翻译
        模型先产出 Assistant Message。若其中含 Tool Call，Pi 执行后把 Tool Result 同时加入当前上下文和本次新增消息。下一轮模型因此能基于真实输出继续，而不是假装命令已经成功。

`packages/agent/src/agent-loop.ts:217-249`

```
			// Stream assistant response
			const message = await streamAssistantResponse(currentContext, config, signal, emit, streamFunction);
			newMessages.push(message);

			if (message.stopReason === "error" || message.stopReason === "aborted") {
				await emit({ type: "turn_end", message, toolResults: [] });
				await emit({ type: "agent_end", messages: newMessages });
				return;
			}

			// Check for tool calls
			const toolCalls = message.content.filter((c) => c.type === "toolCall");

			const toolResults: ToolResultMessage[] = [];
			hasMoreToolCalls = false;
			if (toolCalls.length > 0) {
				// A "length" stop means the output was cut off by the token limit, so
				// every tool call in the message may carry truncated arguments. Fail
				// them all instead of executing potentially borked calls.
				const executedToolBatch =
					message.stopReason === "length"
						? await failToolCallsFromTruncatedMessage(toolCalls, emit)
						: await executeToolCalls(currentContext, message, config, signal, emit);
				toolResults.push(...executedToolBatch.messages);
				hasMoreToolCalls = !executedToolBatch.terminate;

				for (const result of toolResults) {
					currentContext.messages.push(result);
					newMessages.push(result);
				}
			}

			await emit({ type: "turn_end", message, toolResults });
```

预测：assistant提出read，但最终答案引用了不存在的文件，先查哪里？

参考：先查工具是否注册、实际执行、是否返回错误，以及tool result是否进入下一轮上下文；最后再评估模型如何使用正确结果。

### 批次并行与串行约束

默认工具批次可以并行；只要其中一个工具要求顺序，整批就走串行路径。这条调度规则影响完成顺序和共享资源竞争，界面动画无法说明它。

独立文件的并行读取可能缩短等待，同一文件的并行写入则需业务控制。工具结果 ID 不能消除竞争，串行也不自动提供事务或回滚。扩展工具时应声明顺序要求，并用共享资源样例验证。

源码观察：白话翻译
        默认可并行，但任一工具要求顺序执行时，整批改走串行路径。这类约束属于 Agent Core 的执行语义，不应由界面动画决定。

`packages/agent/src/agent-loop.ts:464-478`

```
async function executeToolCalls(
	currentContext: AgentContext,
	assistantMessage: AssistantMessage,
	config: AgentLoopConfig,
	signal: AbortSignal | undefined,
	emit: AgentEventSink,
): Promise<ExecutedToolCallBatch> {
	const toolCalls = assistantMessage.content.filter((c) => c.type === "toolCall");
	const hasSequentialToolCall = toolCalls.some(
		(tc) => currentContext.tools?.find((t) => t.name === tc.name)?.executionMode === "sequential",
	);
	if (config.toolExecution === "sequential" || hasSequentialToolCall) {
		return executeToolCallsSequential(currentContext, assistantMessage, toolCalls, config, signal, emit);
	}
	return executeToolCallsParallel(currentContext, assistantMessage, toolCalls, config, signal, emit);
```

预测：同一批中一个工具必须串行，应该只串行它吗？

参考：此冻结实现会把整批切到串行路径；解释实际批次策略，再独立考虑工具自身的事务与幂等。

### 工具曝光与执行前拦截

默认工具包含 read/bash/edit/write，调用方可以替换或过滤。没有向模型提供工具，与模型提出调用后被策略拒绝，发生在不同阶段。

过滤减少模型可选能力，实际执行仍需检查有效注册表和宿主策略。新增工具要确认名称与实现对应；仅在 Prompt 里写“不要执行”不能作为许可检查。

源码观察：白话翻译
        默认负载是 read、bash、edit、write。配置可以替换默认集合，调用方也能做 allow/exclude/no-tools 过滤；“工具未展示给模型”与“工具展示后再审批”是不同设计。

`packages/coding-agent/src/core/sdk.ts:256-263`

```
	const defaultActiveToolNames: ToolName[] = ["read", "bash", "edit", "write"];
	const configuredDefaultToolNames = settingsManager.getDefaultTools();
	const allowedToolNames = options.tools ?? (options.noTools === "all" ? [] : undefined);
	const excludedToolNames = options.excludeTools;
	const excludedToolNameSet = excludedToolNames ? new Set(excludedToolNames) : undefined;
	const initialActiveToolNames = (
		options.tools ?? (options.noTools ? [] : (configuredDefaultToolNames ?? defaultActiveToolNames))
	).filter((name) => !excludedToolNameSet?.has(name));
```

预测：工具不在模型描述里，是否已经证明不可执行？

参考：只证明当前曝光集合；仍需核对实际注册、外部入口和执行策略。不要从模型看不到直接推出系统没有任何执行通道。

### 项目Trust的范围

未信任项目时，资源加载器排除项目本地 Extension 与 Package；用户级和显式 CLI 资源另有规则。Trust 主要控制进入装配的资源。

读取 AGENTS、加载扩展和执行工具应分别分析。项目被信任，并不意味着 bash 对文件系统和网络的每项操作都已获准。

源码观察：白话翻译
        未信任阶段先排除项目本地 Extension 与 Package，同时仍可加载用户级和临时 CLI 扩展。用户作出 trust 决定后，资源加载器才按该状态重载设置与资源。

`packages/coding-agent/src/core/resource-loader.ts:380-400`

```
	async loadProjectTrustExtensions(): Promise<LoadExtensionsResult> {
		// Force untrusted project settings for the bootstrap pass. This keeps project-local
		// extensions/packages out while still loading user/global and temporary CLI extensions.
		this.settingsManager.setProjectTrusted(false);
		await this.settingsManager.reload();
		return this.loadCurrentExtensionSet({ includeInlineFactories: true });
	}

	async reload(options?: ResourceLoaderReloadOptions): Promise<void> {
		resetTimings("extensions");

		if (this.loaded) {
			clearExtensionCache();
		}

		let preTrustExtensions: LoadExtensionsResult | undefined;
		if (options?.resolveProjectTrust) {
			preTrustExtensions = await this.loadProjectTrustExtensions();
			const projectTrusted = await options.resolveProjectTrust({ extensionsResult: preTrustExtensions });
			this.settingsManager.setProjectTrusted(projectTrusted);
		}
```

预测：项目已Trust，能否据此称bash被沙箱隔离？

参考：不能。Trust是资源准入，bash执行范围由宿主与外部隔离决定；需核对具体sandbox/backend和执行策略。

### 本地Shell与策略接缝

bash 在宿主上启动子进程，采用配置的 cwd 和环境。取消与超时限制进程寿命，文件、进程和网络隔离仍需其他机制；beforeToolCall 提供可配置的执行前策略入口。

研究权限时明确 principal、资源与动作，再检查策略如何生效。本课未执行宿主 shell 工具，也未读取真实凭据；独立教学模型仅演示状态契约，不能证明部署后的策略有效。

源码观察：白话翻译
        内建 bash 工具直接启动本地 shell 子进程，并传入当前工作目录与环境。代码会处理取消、超时和输出，但这些不是资源隔离；真正可访问范围仍由宿主进程决定。

`packages/coding-agent/src/core/tools/bash.ts:80-102`

```
/** Shared process execution used by the built-in shell tools. */
export function createLocalShellOperations(shellName: string, resolveShellConfig: () => ShellConfig): BashOperations {
	return {
		exec: async (command, cwd, { onData, signal, timeout, env }) => {
			const timeoutMs = resolveTimeoutMs(timeout);
			if (signal?.aborted) {
				throw new Error("aborted");
			}
			const shellConfig = resolveShellConfig();
			try {
				await fsAccess(cwd, constants.F_OK);
			} catch {
				throw new Error(`Working directory does not exist: ${cwd}\nCannot execute ${shellName} commands.`);
			}

			const commandFromStdin = shellConfig.commandTransport === "stdin";
			const child = spawn(shellConfig.shell, commandFromStdin ? shellConfig.args : [...shellConfig.args, command], {
				cwd,
				detached: process.platform !== "win32",
				env: env ?? getShellEnv(),
				stdio: [commandFromStdin ? "pipe" : "ignore", "pipe", "pipe"],
				windowsHide: true,
			});
```

预测：希望禁止某类写操作，Prompt足够吗？

参考：在工具集合和执行前策略中明确限制，必要时使用外部隔离；再验证允许/拒绝案例与旁路。自然语言建议不等于强制门禁。

### 事件桥与追加时点

AgentSession 在 message_end 时把消息追加到 SessionManager，自定义消息使用自己的记录类型。因此流中的片段与已经保存的完整消息具有不同生命周期。

若异常发生在消息结束前，先核对事件时点和实际文件内容：UI 显示过文字，并不说明完整消息已保存。随后再查模型历史。日志结构正确也无法回滚此前的工具写入。

源码观察：白话翻译
        AgentSession 同时是事件桥与持久化边界。自定义消息有自己的条目类型；system、user、assistant 和 toolResult 在 message_end 时追加为普通消息条目。

`packages/coding-agent/src/core/agent-session.ts:688-707`

```
		// Handle session persistence
		if (event.type === "message_end") {
			// Check if this is a custom message from extensions
			if (event.message.role === "custom") {
				// Persist as CustomMessageEntry
				this.sessionManager.appendCustomMessageEntry(
					event.message.customType,
					event.message.content,
					event.message.display,
					event.message.details,
				);
			} else if (
				event.message.role === "system" ||
				event.message.role === "user" ||
				event.message.role === "assistant" ||
				event.message.role === "toolResult"
			) {
				// Regular LLM message - persist as SessionMessageEntry
				this.sessionManager.appendMessage(event.message);
			}
```

预测：终端显示了文字，重新打开却没有这条，最先确认什么？

参考：确认message_end是否到达及保存是否成功，再检查当前leaf和上下文重建。可见流块不等于持久记录。

### 物理追加与逻辑分支

消息条目保存 parentId，当前 leaf 成为下一条消息的父节点；branch 只移动 leaf 指针。旧分支仍在同一 JSONL 文件中，不会因移动指针而被删除。

模型输入应沿 root 到当前 leaf 的有效路径构造。教学对照保留 A/B 两条分支，再用全文件读取展示旁支如何混入；物理文件的追加顺序不能替代活动分支。

源码观察：白话翻译
        新消息先记住当前 leaf 作为 parentId，再追加、建索引、把 leaf 移到自己并持久化。压缩摘要与分支摘要故意不是伪装成普通消息的记录。

`packages/coding-agent/src/core/session-manager.ts:1069-1091`

```
	private _appendEntry(entry: SessionEntry): void {
		this.fileEntries.push(entry);
		this.byId.set(entry.id, entry);
		this.leafId = entry.id;
		this._persist(entry);
	}

	/** Append a message as child of current leaf, then advance leaf. Returns entry id.
	 * Does not allow writing CompactionSummaryMessage and BranchSummaryMessage directly.
	 * Reason: we want these to be top-level entries in the session, not message session entries,
	 * so it is easier to find them.
	 * These need to be appended via appendCompaction() and appendBranchSummary() methods.
	 */
	appendMessage(message: Message | CustomMessage | BashExecutionMessage): string {
		const entry: SessionMessageEntry = {
			type: "message",
			id: generateId(this.byId),
			parentId: this.leafId,
			timestamp: new Date().toISOString(),
			message,
		};
		this._appendEntry(entry);
		return entry.id;
```

预测：从旧节点分支后，旧答案被删除了吗？

参考：没有。它仍保留在物理日志；当前leaf只选择新的活动路径。应区分保留历史与本轮模型可见投影。

### 压缩条目与有效尾部

上下文重建先采用最新压缩条目，再接 firstKeptEntryId 之后的有效尾部与后续记录。原话可以留在文件里，却未必逐条进入模型窗口。

分支摘要与压缩摘要属于不同记录类型。核对重要事实时，比较原记录、摘要和实际请求，确认投影保留了什么；摘要存在不能单独证明逐字保真。

源码观察：白话翻译
        重建上下文时，最新压缩条目先出现，然后加入从 firstKeptEntryId 开始的保留尾部，以及压缩之后的新记录。更老的原始消息仍在文件里，但不再逐条发送给模型。

`packages/coding-agent/src/core/session-manager.ts:452-464`

```
	const contextEntries: SessionEntry[] = [compaction];
	let foundFirstKept = false;
	for (let i = 0; i < compactionIdx; i++) {
		const entry = path[i];
		if (entry.id === compaction.firstKeptEntryId) {
			foundFirstKept = true;
		}
		if (foundFirstKept && !(entry.type === "message" && entry.message.role === "system")) {
			contextEntries.push(entry);
		}
	}
	contextEntries.push(...path.slice(compactionIdx + 1));
	return contextEntries;
```

预测：文件还保存早期值，压缩后模型应必然记住吗？

参考：不必然。只有实际投影中保留的原文或摘要明确带入才可见；还需以真实模型probe另验使用效果。

### 扩展接缝的选择

输入、Turn、Message、Tool 和模型选择事件提供扩展位置。需求能在公开接口完成时，通常无需修改核心循环。

hook 的顺序、阻塞方式和返回契约仍会影响执行。先固定一个场景：新增观测检查流消费与延迟是否变化，新增策略检查拒绝结果是否被记录。公开接口也需要行为验证。

源码观察：白话翻译
        公开 API 覆盖输入、Agent、Turn、Message、Tool 与模型选择等测试点，还允许注册新工具和斜杠命令。若需求能在这些接缝完成，通常不必改主循环。

`packages/coding-agent/src/core/extensions/types.ts:1296-1334`

```
	on(
		event: "before_agent_start",
		handler: ExtensionHandler<BeforeAgentStartEvent, BeforeAgentStartEventResult>,
	): () => void;
	on(event: "agent_start", handler: ExtensionHandler<AgentStartEvent>): () => void;
	on(event: "agent_end", handler: ExtensionHandler<AgentEndEvent>): () => void;
	on(event: "agent_settled", handler: ExtensionHandler<AgentSettledEvent>): () => void;
	on(event: "ui_prompt_start", handler: ExtensionHandler<UIPromptStartEvent>): () => void;
	on(event: "ui_prompt_end", handler: ExtensionHandler<UIPromptEndEvent>): () => void;
	on(event: "turn_start", handler: ExtensionHandler<TurnStartEvent>): () => void;
	on(event: "turn_end", handler: ExtensionHandler<TurnEndEvent>): () => void;
	on(event: "message_start", handler: ExtensionHandler<MessageStartEvent>): () => void;
	on(event: "message_update", handler: ExtensionHandler<MessageUpdateEvent>): () => void;
	on(event: "message_end", handler: ExtensionHandler<MessageEndEvent, MessageEndEventResult>): () => void;
	on(event: "tool_execution_start", handler: ExtensionHandler<ToolExecutionStartEvent>): () => void;
	on(event: "tool_execution_update", handler: ExtensionHandler<ToolExecutionUpdateEvent>): () => void;
	on(event: "tool_execution_end", handler: ExtensionHandler<ToolExecutionEndEvent>): () => void;
	on(event: "model_select", handler: ExtensionHandler<ModelSelectEvent>): () => void;
	on(event: "thinking_level_select", handler: ExtensionHandler<ThinkingLevelSelectEvent>): () => void;
	on(event: "tool_call", handler: ExtensionHandler<ToolCallEvent, ToolCallEventResult>): () => void;
	on(event: "tool_result", handler: ExtensionHandler<ToolResultEvent, ToolResultEventResult>): () => void;
	on(event: "user_bash", handler: ExtensionHandler<UserBashEvent, UserBashEventResult>): () => void;
	on(event: "input", handler: ExtensionHandler<InputEvent, InputEventResult>): () => void;

	// =========================================================================
	// Tool Registration
	// =========================================================================

	/** Register a tool that the LLM can call. */
	registerTool<TParams extends TSchema = TSchema, TDetails = unknown, TState = any>(
		tool: ToolDefinition<TParams, TDetails, TState>,
	): void;

	// =========================================================================
	// Command, Shortcut, Flag Registration
	// =========================================================================

	/** Register a custom command. */
	registerCommand(name: string, options: Omit<RegisteredCommand, "name" | "sourceInfo">): void;
```

预测：要记录工具时长，应先改核心Agent loop吗？

参考：先用工具前后事件或公开扩展接口，定义关联ID、失败和取消时的记录；对比启用前后输出与时序后再决定是否改核心。

### 截断工具调用的fail-closed

输出因长度截断时，残缺 JSON 即使还能解析，循环也不会执行这批调用；它为每项生成错误结果，要求完整参数。这条分支同时检查了生成是否结束。

它建立的是协议完成门槛，其他参数安全条件仍需检查。修改 Provider stop reason 映射后，回归正常和截断两类输出，避免不完整请求进入有副作用的工具。

源码观察：白话翻译
        输出长度截断时，即便残缺 JSON 恰好还能解析，Pi 也不执行任何工具调用；它为每个调用生成错误 Tool Result，让模型用完整参数重试。这是具体的 fail-closed 设计。

`packages/agent/src/agent-loop.ts:428-458`

```
 * Fail all tool calls from an assistant message that was truncated by the
 * output token limit. Streamed tool-call arguments are finalized with a
 * best-effort JSON salvage parser, so a truncated message can yield tool calls
 * whose arguments parse and validate but are silently incomplete. None of them
 * are safe to execute; report each as an error so the model can re-issue them.
 */
async function failToolCallsFromTruncatedMessage(
	toolCalls: AgentToolCall[],
	emit: AgentEventSink,
): Promise<ExecutedToolCallBatch> {
	const messages: ToolResultMessage[] = [];
	for (const toolCall of toolCalls) {
		await emit({
			type: "tool_execution_start",
			toolCallId: toolCall.id,
			toolName: toolCall.name,
			args: toolCall.arguments,
		});
		const finalized: FinalizedToolCallOutcome = {
			toolCall,
			result: createErrorToolResult(
				`Tool call "${toolCall.name}" was not executed: the response hit the output token limit, so its arguments may be truncated. Re-issue the tool call with complete arguments.`,
			),
			isError: true,
		};
		await emitToolExecutionEnd(finalized, emit);
		const toolResultMessage = createToolResultMessage(finalized);
		await emitToolResultMessage(toolResultMessage, emit);
		messages.push(toolResultMessage);
	}
	return { messages, terminate: false };
```

预测：截断输出里的参数碰巧是合法JSON，能否执行？

参考：此实现仍拒绝整批并生成错误ToolResult。必须同时满足完整输出与合法调用契约，不能仅看JSON可解析。

### 用失败层次教回主线

没有模型或有效认证时，运行在进入循环前终止；OAuth 错误另有反馈。排错时将这些前置问题与模型能力、工具错误和会话重建分别归类。

迁移宿主前，固定输入变换、循环事件、工具策略、日志树与上下文投影。静态源码、独立模型与真实 Provider 结果分别记录。当前教材未发送真实模型请求，也未验证 OS 隔离。

源码观察：白话翻译
        没有模型或没有有效认证时，请求在 Agent Loop 之前终止。OAuth 错误还会给出重新登录的具体动作；这类故障不应通过重写 Prompt 修复。

`packages/coding-agent/src/core/agent-session.ts:1313-1330`

```
			// Validate model
			if (!this.model) {
				throw new Error(formatNoModelSelectedMessage());
			}

			const hasConfiguredAuth =
				this._modelRuntime.hasConfiguredAuth(this.model.provider) ||
				(await this._modelRuntime.checkAuth(this.model.provider)) !== undefined;
			if (!hasConfiguredAuth) {
				const isOAuth = this._modelRuntime.isUsingOAuth(this.model.provider);
				if (isOAuth) {
					throw new Error(
						`Authentication failed for "${this.model.provider}". ` +
							`Credentials may have expired or network is unavailable. ` +
							`Run '/login ${this.model.provider}' to re-authenticate.`,
					);
				}
				throw new Error(formatNoApiKeyFoundMessage(this.model.provider));
```

预测：迁移为研究助手，最先应冻结哪几个契约？

参考：冻结输入/模型配置、工具权限与结果配对、终止条件、会话树与压缩投影；再分别验证正常、截断、拒绝和恢复，不拿CLI最终文字代替证据。

### 闭卷复述与迁移

保留两个会话分支时，为什么不能把整个 JSONL 按时间顺序直接发给模型？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## LangGraph · 状态图的可见性与提交

状态图的可见性与提交

来源：https://github.com/langchain-ai/langgraph

提交：`aa742fb31e2827d569b843e3600aeda2e0528e4b`；访问：2026-10-02

证据：独立教学模型3组固定正/错误策略对照；不导入上游，不构成生产Runtime验证。

重点检查节点重入、消息 ID 合并与外部副作用。

排除：真实模型与供应商质量；真实沙箱/鉴权与部署；跨进程持久恢复及外部副作用恰好一次；并发压力与生产竞态；学习者实际作答及掌握度

### 本案例阅读任务

预测图中节点何时读到更新，以及 checkpoint 和 interrupt 怎样影响后续执行。

读前准备：第 4、6 章；知道 Python 类型注解。superstep 是一次计划、执行和提交的步边界。

1. 先读 StateGraph 与 compile，分开记录图结构和运行配置。
2. 用两个并行节点预测 reducer 和 add_messages 的合并结果。
3. 追 checkpoint 身份及 interrupt 恢复，标出重入与外部副作用。

检验理解：恢复一个含 interrupt 的节点时，哪些代码可能重跑，哪些外部动作不会自动回滚？

判断标准：说明恢复值的匹配和节点重入；将图状态分叉与文件、数据库等外部状态分开。

阅读主线：从 StateGraph 到 reducer、superstep、checkpoint 和 interrupt，预测下一步读到什么。

### Builder 与可执行图分开

StateGraph 描述状态 schema、节点和边；节点返回局部更新，compile 后得到可调用对象。构图阶段检查连接与类型，运行阶段处理实际状态和异常。

看工作流图时，也记录 compile 采用的 checkpointer 和 interrupt 设置。同一个 builder 可以因编译配置不同而产生不同执行行为；未编译的构图对象还不能代替实际运行对象。

源码观察：白话翻译
        节点通过共享 state 交换信息，但每个节点只交回局部更新。StateGraph 只是构造器；没有 compile()，就不存在可调用或可流式运行的图。

`libs/langgraph/langgraph/graph/state.py:131-145`

```
class StateGraph(Generic[StateT, ContextT, InputT, OutputT]):
    """A graph whose nodes communicate by reading and writing to a shared state.

    The signature of each node is `State -> Partial<State>`.

    Each state key can optionally be annotated with a reducer function that
    will be used to aggregate the values of that key received from multiple nodes.
    The signature of a reducer function is `(Value, Value) -> Value`.

    !!! warning

        `StateGraph` is a builder class and cannot be used directly for execution.
        You must first call `.compile()` to create an executable graph that supports
        methods like `invoke()`, `stream()`, `astream()`, and `ainvoke()`. See the
        `CompiledStateGraph` documentation for more details.
```

预测：同一 builder 编译两次一定行为相同吗？

参考：不一定。checkpointer、interrupt、store 等编译参数影响执行。先冻结图定义与编译选项，再比较行为。

### 子图是节点也是边界

编译后的子图可以加入父图节点。嵌套并不是把所有内部节点复制进父图：状态接口、执行命名空间和观测层级需要分别理解。

先画父节点的输入输出，再进入子图看局部读写；事件流若带子图信息，应保留对应身份。图的嵌套结构不自动证明两个层级拥有同一 checkpoint 寿命。

源码观察：白话翻译
        这个上游端到端测试先把内部图编译，再把它当成外部图的一个节点。START 与 END 是入口和终点标记；真正的业务工作由两个 node 完成。

`libs/langgraph/tests/test_stream_events_v3_e2e.py:59-77`

```
    def process_node(state: AgentState) -> dict[str, Any]:
        return {"value": state["value"] + "_processed", "items": ["processed"]}

    inner_builder: StateGraph = StateGraph(AgentState, input_schema=AgentState)
    inner_builder.add_node("process_node", process_node)
    inner_builder.add_edge(START, "process_node")
    inner_builder.add_edge("process_node", END)
    inner_graph = inner_builder.compile()

    def router_node(state: AgentState) -> dict[str, Any]:
        return {"value": state["value"] + "_routed", "items": ["routed"]}

    outer_builder: StateGraph = StateGraph(AgentState, input_schema=AgentState)
    outer_builder.add_node("router", router_node)
    outer_builder.add_node("inner", inner_graph)
    outer_builder.add_edge(START, "router")
    outer_builder.add_edge("router", "inner")
    outer_builder.add_edge("inner", END)
    return outer_builder.compile()
```

预测：看到一个子图节点，追踪应先做什么？

参考：先确认父图向该节点传递与接收的状态字段，再看子图内部节点和 checkpoint/namespace 边界；不能仅从图名合并全部历史。

### compile 固定运行条件

编译把 schema、通道、节点与运行选项交给 CompiledStateGraph。读源码应把静态结构和运行时配置放在两列，而不是只看 add_edge。

外部 thread_id 不属于图拓扑，却决定带 checkpointer 的恢复上下文。没有固定编译和调用配置，两个看起来相同的示例不构成可比实验。

源码观察：白话翻译
        编译边界不只是换名字：它把 checkpointer、暂停点、缓存等运行策略固定进一个 CompiledStateGraph。从此调用的是可执行对象，而不是继续修改蓝图。

`libs/langgraph/langgraph/graph/state.py:1177-1192`

```
    def compile(
        self,
        checkpointer: Checkpointer = None,
        *,
        cache: BaseCache | None = None,
        store: BaseStore | None = None,
        interrupt_before: All | list[str] | None = None,
        interrupt_after: All | list[str] | None = None,
        debug: bool = False,
        name: str | None = None,
        transformers: Sequence[Callable[[tuple[str, ...]], Any]] | None = None,
    ) -> CompiledStateGraph[StateT, ContextT, InputT, OutputT]:
        """Compiles the `StateGraph` into a `CompiledStateGraph` object.

        The compiled graph implements the `Runnable` interface and can be invoked,
        streamed, batched, and run asynchronously.
```

预测：重复同一个输入却读到旧状态，先核对什么？

参考：核对 checkpointer 是否启用、thread_id/namespace 与调用配置，再区分新运行和恢复；同输入不意味着空历史。

### Reducer 决定更新语义

普通状态字段常按最后值通道处理；Annotated 字段可以声明 reducer，例如 operator.add 归并列表。节点返回局部更新不等于覆盖整个 state。

两个并行节点写同一字段时，先查通道是否允许这些写入，再查 reducer 怎样合并。不能直接套用 JSON 字典的最后写入覆盖规则，否则会遗漏图对并发更新的约束。

源码观察：白话翻译
        value 没有额外合并标注；items 明确用 operator.add 把旧列表与新列表相加。两个 node 都写 items 时，不应把它当普通覆盖字段。

`libs/langgraph/tests/test_stream_events_v3_e2e.py:42-44`

```
class AgentState(TypedDict):
    value: str
    items: Annotated[list[str], operator.add]
```

预测：两个节点都写 items，结果一定是最后一个列表吗？

参考：先查 items 的 reducer；add 归并与最后值语义不同。明确通道是否接受并发写入，再预测结果。

### add_messages 按ID而非正文

add_messages 为消息补齐身份，按消息 ID 归并：新 ID 追加，同 ID 更新可以替换，RemoveMessage 另有删除语义。它不是普通列表拼接。

同一消息内容相同但 ID 不同仍是两条；内容改变但 ID 相同可能是修订。迁移事件记录时丢 ID 会把修订变成重复，模型上下文也随之改变。

源码观察：白话翻译
        没有 ID 的消息先获分配 ID；新 ID 追加，已有 ID 替换，RemoveMessage 标记删除。这个 reducer 维护的是“可更新的消息集合”，不只是 left + right。

`libs/langgraph/langgraph/graph/message.py:202-234`

```
    # assign missing ids
    for m in left:
        if m.id is None:
            m.id = str(uuid.uuid4())
    for idx, m in enumerate(right):
        if m.id is None:
            m.id = str(uuid.uuid4())
        if isinstance(m, RemoveMessage) and m.id == REMOVE_ALL_MESSAGES:
            remove_all_idx = idx

    if remove_all_idx is not None:
        return right[remove_all_idx + 1 :]

    # merge
    merged = left.copy()
    merged_by_id = {m.id: i for i, m in enumerate(merged)}
    ids_to_remove = set()
    for m in right:
        if (existing_idx := merged_by_id.get(m.id)) is not None:
            if isinstance(m, RemoveMessage):
                ids_to_remove.add(m.id)
            else:
                ids_to_remove.discard(m.id)
                merged[existing_idx] = m
        else:
            if isinstance(m, RemoveMessage):
                raise ValueError(
                    f"Attempting to delete a message with an ID that doesn't exist ('{m.id}')"
                )

            merged_by_id[m.id] = len(merged)
            merged.append(m)
    merged = [m for m in merged if m.id not in ids_to_remove]
```

预测：ID=1 的消息更新正文，会出现两条ID=1吗？

参考：按 add_messages 的正常归并路径替换原ID位置；新ID才追加。删除消息按 RemoveMessage 的专门协议处理。

### 测试用例帮助冻结边界

同 ID 替换的测试是可定位的契约样例。它支持理解归并行为，但本教程只引用该测试源码，没有把引用当执行通过记录。

为自己的应用补验证时，固定新 ID 追加、同 ID 替换和删除不存在 ID 三类输入。先定义希望保持的消息身份，再选择 reducer；不要只用一条聊天成功示例验收。

源码观察：白话翻译
        新写入沿用 ID 1，结果不是两条消息，而是原位置的内容被更新。

`libs/langgraph/tests/test_messages_state.py:55-60`

```
def test_update_existing_message():
    left = [HumanMessage(content="Hello", id="1")]
    right = HumanMessage(content="Hello again", id="1")
    result = add_messages(left, right)
    expected_result = [HumanMessage(content="Hello again", id="1")]
    assert result == expected_result
```

预测：读取 test_messages_state 能报告运行通过吗？

参考：不能。静态测试源码说明预期；执行结果必须有真实命令、环境、退出码与输出。本包教学模型另列证据层。

### Superstep 分计划、执行和提交

Pregel 先按上一步的通道值选择任务，再执行本步节点，最后统一提交写入。本步更新通常到下一步才对其他任务可见；读调度器时要标出这三个阶段。

这让同时运行的节点基于一致的旧状态推理。把其中一个任务先写入共享 state，再让另一个即时读取，会产生受完成顺序影响的不同语义。

源码观察：白话翻译
        Plan 看“上一轮哪些 channel 变了”来选 actor；Execution 让本轮 actor 工作；Update 才把所有写入提交。运行结束条件不是“某个节点返回了”，而是再也没有 actor 被选中或达到步数上限。

`libs/langgraph/langgraph/pregel/main.py:454-477`

```
    """Pregel manages the runtime behavior for LangGraph applications.

    ## Overview

    Pregel combines [**actors**](https://en.wikipedia.org/wiki/Actor_model)
    and **channels** into a single application.
    **Actors** read data from channels and write data to channels.
    Pregel organizes the execution of the application into multiple steps,
    following the **Pregel Algorithm**/**Bulk Synchronous Parallel** model.

    Each step consists of three phases:

    - **Plan**: Determine which **actors** to execute in this step. For example,
        in the first step, select the **actors** that subscribe to the special
        **input** channels; in subsequent steps,
        select the **actors** that subscribe to channels updated in the previous step.
    - **Execution**: Execute all selected **actors** in parallel,
        until all complete, or one fails, or a timeout is reached. During this
        phase, channel updates are invisible to actors until the next step.
    - **Update**: Update the channels with the values written by the **actors**
        in this step.

    Repeat until no **actors** are selected for execution, or a maximum number of
    steps is reached.
```

预测：A/B 同步开始，B能直接看到A本步刚写的值吗？

参考：按主线 superstep 语义，本步执行看到已提交状态；A本步写入在更新阶段提交，下一步才用于调度与读取。

### 任务准备不是节点已经完成

循环根据 checkpoint、pending writes、触发条件和任务配置准备本步工作。准备好的任务可能还会命中缓存、重试或被 interrupt 阻止执行。

调试重复调用时区分任务 ID、调度、实际执行、写入提交四阶段。仅在日志出现节点名不能证明节点代码已经产生副作用。

源码观察：白话翻译
        runtime 不是简单沿一条 Python 调用栈向下走。它用 checkpoint、pending writes、channel 变化和触发映射算出本轮 task 集合，重试与缓存策略也在这里进入调度。

`libs/langgraph/langgraph/pregel/_loop.py:611-629`

```
        # prepare next tasks
        self.tasks = prepare_next_tasks(
            self.checkpoint,
            self.checkpoint_pending_writes,
            self.nodes,
            self.channels,
            self.managed,
            self.config,
            self.step,
            self.stop,
            for_execution=True,
            manager=self.manager,
            store=self.store,
            checkpointer=self.checkpointer,
            trigger_to_nodes=self.trigger_to_nodes,
            updated_channels=self.updated_channels,
            retry_policy=self.retry_policy,
            cache_policy=self.cache_policy,
        )
```

预测：监控看到 scheduled，能认为外部API已调用吗？

参考：不能。继续核对实际执行、缓存/中断/重试和提交事件。任务准备与外部副作用发生分别观察。

### 统一提交使下一步有稳定状态

after_tick 汇总已完成任务的写入、应用通道更新并推进 checkpoint。发出 values 和清理 pending writes 属于步边界，而不是每个函数调用随意覆盖。

节点失败、重试和保存失败需要分层定位。只看最后流块无法知道哪些写入已被接受；要结合状态快照与任务错误判断可恢复点。

源码观察：白话翻译
        after_tick() 汇总 task writes，交给 channel 规则应用；必要时发出完整 values，再清 pending writes、退出 replay 标志并保存本轮 checkpoint。

`libs/langgraph/langgraph/pregel/_loop.py:683-718`

```
    def after_tick(self) -> None:
        # finish superstep
        writes = [w for t in self.tasks.values() for w in t.writes]
        self._delta_channels_with_overwrite.update(
            ch
            for ch, v in writes
            if isinstance(self.specs.get(ch), DeltaChannel) and _get_overwrite(v)[0]
        )
        # all tasks have finished
        self.updated_channels = apply_writes(
            self.checkpoint,
            self.channels,
            self.tasks.values(),
            self.checkpointer_get_next_version,
            self.trigger_to_nodes,
        )
        # produce values output
        if not self.updated_channels.isdisjoint(
            (self.output_keys,)
            if isinstance(self.output_keys, str)
            else self.output_keys
        ):
            self._emit(
                "values", map_output_values, self.output_keys, writes, self.channels
            )
        # capture delta-channel writes for exit-mode accumulator before clearing
        if self._exit_delta_writes is not None:
            for tid, ch, v in self.checkpoint_pending_writes:
                if isinstance(self.specs.get(ch), DeltaChannel):
                    self._exit_delta_writes.append((self.step, tid, ch, v))
        # clear pending writes
        self.checkpoint_pending_writes.clear()
        # only replay (re-execute) done tasks on the first tick
        self.is_replaying = False
        # save checkpoint
        self._put_checkpoint({"source": "loop"})
```

预测：节点输出已打印，checkpoint一定已保存吗？

参考：不一定。节点输出、通道提交、流事件和存储成功是不同观察点；检查步边界与 checkpointer 记录。

### 路由看结构化 tool_calls

tools_condition 查看最后消息是否携带工具调用，从而转向 tools 或 END。自然语言说“调用了搜索”不能代替结构化调用字段。

输入可能是消息列表、带 messages 的状态或对应对象。接入自定义状态时先确认路由读取的消息键，避免因字段名错位而意外结束。

源码观察：白话翻译
        函数兼容消息列表、字典 State 与有 messages 属性的对象；最终只检查最后消息。存在 tool calls 就返回 tools，否则返回终点标记。

`libs/prebuilt/langgraph/prebuilt/tool_node.py:1648-1659`

```
    if isinstance(state, list):
        ai_message = state[-1]
    elif (isinstance(state, dict) and (messages := state.get(messages_key, []))) or (
        messages := getattr(state, messages_key, [])
    ):
        ai_message = messages[-1]
    else:
        msg = f"No messages found in input state to tool_edge: {state}"
        raise ValueError(msg)
    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
        return "tools"
    return "__end__"
```

预测：assistant 正文写“搜索中”却无 tool_calls，会走tools吗？

参考：主线路由依据结构化 tool_calls，不依据正文。先核对消息类型与键，再检查模型绑定工具是否正确。

### ToolNode 与模型职责分离

ToolNode 将请求分派给可用工具，处理并行与错误策略，并可以读取图 state/store 注入参数。工具描述、模型决定和执行节点是三个责任。

state 注入是调用数据通道，不等于工具拥有全部用户权限。执行外部写入时仍需应用鉴权、幂等和审计，框架路由不能替代业务控制。

源码观察：白话翻译
        ToolNode 是工具工作间，而不是模型。它处理调用、状态注入、持久 store、并行与错误；当前源码还明确把“自定义细粒度工作流”和标准 ReAct agent 分成两个入口。

`libs/prebuilt/langgraph/prebuilt/tool_node.py:622-635`

```
class ToolNode(RunnableCallable):
    """A node for executing tools in LangGraph workflows.

    Handles tool execution patterns including function calls, state injection,
    persistent storage, and control flow. Manages parallel execution,
    error handling.

    Use `ToolNode` when building custom workflows that require fine-grained control over
    tool execution—for example, custom routing logic, specialized error handling, or
    non-standard agent architectures.

    For standard ReAct-style agents, use [`create_agent`][langchain.agents.create_agent]
    instead. It uses `ToolNode` internally with sensible defaults for the agent loop,
    conditional routing, and error handling.
```

预测：把工具绑定模型后，是否可以删除 ToolNode？

参考：绑定通常只让模型产生请求；仍需执行并生成对应工具结果的机制。若换自定义执行器，也要保持请求身份与错误契约。

### 静态中断发生在工具执行前

编译配置 interrupt_before 指定节点暂停；循环可以在任务已计划但 runner 尚未执行时停住。这个位置适合审阅即将执行的动作。

暂停不代表取消，也不自动提供用户授权。恢复条件与审批信息由应用定义；必须核对暂停时的下一步任务和实际执行计数，证明工具还未运行。

源码观察：白话翻译
        任务已被 Plan 选中，但 runner 尚未执行它；命中名单就把状态标成 interrupt_before 并抛出控制信号。下一章的动态 interrupt() 则发生在节点函数内部。

`libs/langgraph/langgraph/pregel/_loop.py:666-671`

```
        # before execution, check if we should interrupt
        if self.interrupt_before and should_interrupt(
            self.checkpoint, self.interrupt_before, self.tasks.values()
        ):
            self.status = "interrupt_before"
            raise GraphInterrupt()
```

预测：interrupt_before tools 后打印 pending task，工具已执行了吗？

参考：先核对 runner 是否启动。静态中断主线发生在执行前，pending 不证明运行；恢复还需应用明确提供的继续条件。

### thread、namespace、checkpoint 三层身份

内存实现按 thread_id、checkpoint namespace 和 checkpoint_id 组织版本，再保存任务写入。thread_id 指一条历史范围，不是每一步唯一的快照 ID。

两个用户共用 thread_id 可能混合历史；同线程不同子图命名空间也不能只用字符串拼成一列。持久化适配器必须保持版本与命名空间契约。

源码观察：白话翻译
        当前课程引用的测试使用内存 saver，是为了可控地观察语义。源码明确把它限定为调试或测试用途，因此不能据此声称进程重启、并发、备份或生产恢复已解决。

`libs/checkpoint/langgraph/checkpoint/memory/__init__.py:33-42`

```
class InMemorySaver(
    BaseCheckpointSaver[str], AbstractContextManager, AbstractAsyncContextManager
):
    """An in-memory checkpoint saver.

    This checkpoint saver stores checkpoints in memory using a `defaultdict`.

    Note:
        Only use `InMemorySaver` for debugging or testing purposes.
        For production use cases we recommend installing [langgraph-checkpoint-postgres](https://pypi.org/project/langgraph-checkpoint-postgres/) and using `PostgresSaver` / `AsyncPostgresSaver`.
```

预测：只保存thread_id就能精确回到某一步吗？

参考：不能。thread确定历史范围，还需 checkpoint_id 和 namespace 定位具体版本；同时验证身份隔离。

### Memory saver 是测试存储

源码明确把内存 checkpointer 用于调试测试。进程结束后无独立持久介质保证，不能把一次 resume 成功推广为跨进程可靠恢复。

教程选择它解释索引结构；生产持久化候选应另测事务、失败重试、版本兼容与并发。存储 API 可替换不等于故障语义完全一致。

源码观察：白话翻译
        checkpointer 是版本化状态后端，thread_id 是检索键。不同运行用不同 ID 隔离；复用同一 ID 会沿该谱系继续积累状态。它并不指向某个唯一 checkpoint。

`libs/langgraph/langgraph/graph/state.py:1194-1214`

```
        Args:
            checkpointer: A checkpoint saver object or flag.

                If provided, this `Checkpointer` serves as a fully versioned "short-term memory" for the graph,
                allowing it to be paused, resumed, and replayed from any point.

                If `None`, it may inherit the parent graph's checkpointer when used as a subgraph.

                If `False`, it will not use or inherit any checkpointer.

                **Important**: When a checkpointer is enabled, you should pass a `thread_id`
                in the config when invoking the graph:

                ```python
                config = {"configurable": {"thread_id": "my-thread"}}
                graph.invoke(inputs, config)
                ```

                The `thread_id` is the key used to store and retrieve checkpoints. Use a
                unique ID for independent runs, or reuse the same ID to accumulate state
                across invocations (e.g., for conversation memory).
```

预测：Notebook 中恢复成功，重启机器后一定能恢复吗？

参考：不一定。核对存储介质与生命周期；内存对象并未证明持久性，跨进程恢复必须用对应存储独立实测。

### 动态 interrupt 会重入节点

节点中的 interrupt 发出暂停，Command 提供 resume 值。重新执行时，恢复值按 interrupt 调用顺序匹配；恢复通常从节点开头重跑，需要核对前半段是否含副作用。

在 interrupt 前发送邮件或扣款会有重复风险。把副作用放到可幂等节点、使用稳定请求 ID，或将审批与行动拆开；调用次序改变也可能破坏已有恢复值匹配。

源码观察：白话翻译
        存储键把 thread、checkpoint namespace 与 checkpoint ID 分层；writes 还细到 task 和 write index。仅用“一个聊天 ID 对应一份 JSON”来理解，会漏掉历史页与分支。

`libs/checkpoint/langgraph/checkpoint/memory/__init__.py:68-83`

```
    # thread ID ->  checkpoint NS -> checkpoint ID -> checkpoint mapping
    storage: defaultdict[
        str,
        dict[str, dict[str, tuple[tuple[str, bytes], tuple[str, bytes], str | None]]],
    ]
    # (thread ID, checkpoint NS, checkpoint ID) -> (task ID, write idx)
    writes: defaultdict[
        tuple[str, str, str],
        dict[tuple[str, int], tuple[str, str, tuple[str, bytes], str]],
    ]
    blobs: dict[
        tuple[
            str, str, str, str | int | float
        ],  # thread id, checkpoint ns, channel, version
        tuple[str, bytes],
    ]
```

预测：interrupt前计数加1，恢复后一定只加一次吗？

参考：不能这样保证，节点可能重入。副作用要幂等或拆分；确认 resume 值和 interrupt 顺序匹配。

### StateSnapshot 表达下一步与错误

快照除了 values，还包含 next、config、parent_config、tasks 和 interrupts。状态内容正确与运行是否结束是不同问题。

定位卡住时先看 next 和 task error，再看值；历史父配置能说明快照沿革。只截取 values 会丢失重试与暂停信息。

源码观察：白话翻译
        一帧包含已提交 channel values、下一批 node、可再次寻址的 config、父帧、tasks 与未解决 interrupts。调试时不要只打印最终字典；next 和 tasks 才能解释图为何停在这里。

`libs/langgraph/langgraph/types.py:711-729`

```
class StateSnapshot(NamedTuple):
    """Snapshot of the state of the graph at the beginning of a step."""

    values: dict[str, Any] | Any
    """Current values of channels."""
    next: tuple[str, ...]
    """The name of the node to execute in each task for this step."""
    config: RunnableConfig
    """Config used to fetch this snapshot."""
    metadata: CheckpointMetadata | None
    """Metadata associated with this snapshot."""
    created_at: str | None
    """Timestamp of snapshot creation."""
    parent_config: RunnableConfig | None
    """Config used to fetch the parent snapshot, if any."""
    tasks: tuple[PregelTask, ...]
    """Tasks to execute in this step. If already attempted, may contain an error."""
    interrupts: tuple[Interrupt, ...]
    """Interrupts that occurred in this step that are pending resolution."""
```

预测：values已包含答案，图一定结束了吗？

参考：不一定。检查 next、tasks、interrupts 和运行状态，values只是当前数据，不是完整生命周期证明。

### 流事件可报告中断与部分结果

一次运行中断仍可能已有前序步骤的状态值和流事件。流式 UI 需要表现部分产物及暂停原因，不能把看到文本当完整完成。

事件类型和订阅版本是观测契约；本课冻结的测试说明该版本预期，未测真实网络传输或事件恰好一次。重连时仍应结合持久快照。

源码观察：白话翻译
        当前提交的上游测试检查了两层证据：run 被标为 interrupted 且暴露 interrupts；与此同时，output 与 values 投影仍包含暂停前已经完成的 step1。

`libs/langgraph/tests/test_stream_events_v3_e2e.py:470-492`

```
    def test_interrupt_sets_flags_and_surfaces_interrupts(self) -> None:
        """Interrupted run has correct flags and interrupt payloads."""
        graph = _make_interrupt_graph()
        config: dict[str, Any] = {"configurable": {"thread_id": "int-1"}}
        run = graph.stream_events({"value": "x", "items": []}, config, version="v3")

        output = run.output
        assert output is not None
        assert run.interrupted is True
        assert len(run.interrupts) > 0
        assert output["items"] == ["step1"]
        assert "_step1" in output["value"]

    def test_interrupt_values_snapshot_has_partial_state(self) -> None:
        """Values snapshots captured before the interrupt reflect partial state."""
        graph = _make_interrupt_graph()
        config: dict[str, Any] = {"configurable": {"thread_id": "int-2"}}
        run = graph.stream_events({"value": "x", "items": []}, config, version="v3")

        snapshots = list(run.values)
        assert len(snapshots) >= 1
        last = snapshots[-1]
        assert "step1" in last["items"]
```

预测：客户端已收到部分values，中断时要丢弃全部吗？

参考：按应用定义区分已提交部分状态和未完成任务；保留中断原因与可恢复配置，不能宣称完整成功或随意丢掉有效证据。

### 历史分叉不等于从零运行

time-travel 示例选择旧 checkpoint 后再次 resume，形成新答案分支；已在该 checkpoint 之前完成的节点不必全部重跑，而暂停节点可重入。

图历史分叉不会自动撤销文件、数据库或远程操作。将这种恢复迁移到 Agent Runtime 时，还需要定义副作用账本和幂等规则，分别记录图状态与外部状态。

源码观察：白话翻译
        测试先用 old_answer 完成原运行，再找到 next == ("ask_human",) 的历史帧。用该帧 config 调用后，ask_human 再次暂停，node_a 没重跑，并出现来源为 fork 的最新 checkpoint。

`libs/langgraph/tests/test_time_travel.py:339-371`

```
    # --- Original run: invoke until interrupt, then resume to complete ---
    graph.invoke({"value": []}, config)
    graph.invoke(Command(resume="old_answer"), config)

    original_history = list(graph.get_state_history(config))
    original = _checkpoint_summary(original_history)
    assert [(s["source"], s["next"], s["values"]) for s in original] == [
        ("loop", (), {"value": ["a", "human:old_answer", "b"]}),
        ("loop", ("node_b",), {"value": ["a", "human:old_answer"]}),
        ("loop", ("ask_human",), {"value": ["a"]}),
        ("loop", ("node_a",), {"value": []}),
        ("input", ("__start__",), {"value": []}),
    ]

    # --- Replay from checkpoint before ask_human ---
    before_ask = next(s for s in original_history if s.next == ("ask_human",))

    called.clear()
    replay_result = graph.invoke(None, before_ask.config)
    assert replay_result["__interrupt__"][0].value == "What is your input?"
    assert "ask_human" in called
    assert "node_a" not in called  # before the replay point, not re-executed

    # A fork checkpoint is now the latest — it branches from the replay point
    post_replay = _checkpoint_summary(list(graph.get_state_history(config)))
    assert [(s["source"], s["next"]) for s in post_replay] == [
        ("fork", ("ask_human",)),  # <-- new fork (latest)
        ("loop", ()),  # original done
        ("loop", ("node_b",)),
        ("loop", ("ask_human",)),  # branch point
        ("loop", ("node_a",)),
        ("input", ("__start__",)),
    ]
```

预测：从旧checkpoint分叉，新旧答案如何处理？

参考：保留父配置与不同分支的版本身份；根据起点决定重执行范围。外部副作用需独立管理，checkpoint不会自动撤销。

### 闭卷复述与迁移

恢复一个含 interrupt 的节点时，哪些代码可能重跑，哪些外部动作不会自动回滚？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## Eino · Go 类型契约怎样约束执行图

Go 类型契约怎样约束执行图

来源：https://github.com/cloudwego/eino

提交：`58d184303f4e73413c454a9626f79c17af0fd9fb`；访问：2026-10-02

证据：真实 Eino 包六个确定性 Go 测试通过；脚本模型/只读本地工具，无真实模型调用。

原六案例使用脚本模型，未调用付费 API；持久恢复仍需独立验证。

排除：外部模型与推理质量、供应商 tools 支持；checkpoint 保存/恢复、跨版本/跨进程持久性及故障注入；并发压力、callback 时序、多 Agent/DeepAgent、多模态；MCP/沙箱/部署/HTTP鉴权及外部副作用恰好一次；学习者真实作答与掌握程度

### 本案例阅读任务

用类型、消息和流接口追踪 Go 执行图，再通过六个已有框架案例理解工具循环的验证范围。

读前准备：第 3、4 章；能阅读 Go 函数。interface、类型参数和 context.Context 在首个概念中解释。

1. 先读组件类型和 Runnable 四种输入输出形态。
2. 沿消息 ID、流的消费责任、图连接与工具注册追一次调用。
3. 对照六个测试的断言，再单独阅读未运行的 checkpoint 与恢复路径。

检验理解：把类型链、工具循环和恢复分别归入已运行或静态观察，并说明各自能够证明什么。

判断标准：六个测试属于真实 Eino 包配脚本模型；真实 Provider、跨进程恢复和生产并发仍未验证。

阅读主线：由模型/工具接口进入消息流、类型图和 ADK；用六个原真实框架案例对照解释。

### 类型参数与组件接口

从一个小任务读起：输入订单编号，读出金额，再生成摘要。Eino 组织这些步骤，应用提供订单存储、HTTP 服务、模型供应商和用户权限。先找到组件的输入输出类型，再进入内部调度器；目录数量不能说明应用网站已经具备哪些功能。

Go 的 interface 描述一组方法；实现这些方法的类型就能被接入，不需要继承框架基类。BaseModel[M] 的 M 是消息类型参数，Generate 收取消息切片并返回一条消息，Stream 则返回消息流。context.Context 用于传播取消、期限和调用范围数据；它不是永久数据库。error 是独立返回值，调用者必须处理。

本课使用默认的 *schema.Message 路线。当前源码还提供 *schema.AgenticMessage 与 Typed API，后者不能通过随意强制转换接入前者。读到类型别名时先找泛型本体；旧文章里的同名接口可能已经废弃。

源码观察：BaseModel 同时定义完整响应与流式响应，并以消息类型 M 参数化。

`components/model/interface.go:31-39`

```
// BaseModel is the generic base model interface parameterized by message type M.
// It exposes two modes of interaction:
//   - [BaseModel.Generate]: blocks until the model returns a complete response.
//   - [BaseModel.Stream]: returns a [schema.StreamReader] that yields message
//     chunks incrementally as the model generates them.
type BaseModel[M messageType] interface {
	Generate(ctx context.Context, input []M, opts ...Option) (M, error)
	Stream(ctx context.Context, input []M, opts ...Option) (*schema.StreamReader[M], error)
}
```

预测：一个自定义模型只有 Generate，没有 Stream，能否直接满足 BaseModel？怎样定位接口不匹配？

参考：不能。BaseModel 要求两种方法及完全匹配的参数、选项和返回类型。编译错误先对照 components/model/interface.go，再决定补适配方法或选用其他组件契约。

### 工具元信息与执行分开

“计算订单”函数可以直接写成 Go 函数；让模型使用它时，还需要名称、说明、参数描述和调用约定。Info 是可见能力的目录项，InvokableRun 是实际执行入口。只有名称的元信息并不会执行任何业务；模型返回一个工具请求，也还没有调用本地函数。

标准工具入口接收 JSON 字符串，返回字符串与错误。工具可以自己解析，也可以用 utils.InferTool 从 Go 参数结构生成描述并包裹编解码。这里要分清类型检查与业务检查：金额为负、订单不属于当前用户、同一个退款请求重复提交，都需要应用的明确规则。

本课订单工具只做两个整数求和，没有网络或写入。这个最小正对照用于确认工具能接入框架，尚未实现生产订单服务。改成数据库工具后，还要分别验证查询权限、单位、溢出、超时和结果脱敏；自然语言工具说明不能完成这些检查。

源码观察：BaseTool 描述工具；InvokableTool 在其上增加 JSON 参数执行方法。

`components/tool/interface.go:32-46`

```
type BaseTool interface {
	Info(ctx context.Context) (*schema.ToolInfo, error)
}

// InvokableTool is a tool that can be executed by ToolsNode.
//
// InvokableRun receives the model's tool call arguments as a JSON-encoded
// string and returns a plain string result that is sent back to the model as
// a tool message. The framework handles JSON decoding automatically when using
// the [utils.InferTool] or [utils.NewTool] constructors.
type InvokableTool interface {
	BaseTool

	// InvokableRun executes the tool with arguments encoded as a JSON string.
	InvokableRun(ctx context.Context, argumentsInJSON string, opts ...Option) (string, error)
```

预测：模型已返回 sum_order 的名称和参数，在哪一层确认执行过？

参考：检查 ToolsNode 是否找到工具、调用执行方法并返回与请求 ID 匹配的 ToolMessage。仅有 ToolInfo 或 assistant.ToolCalls 不能证明执行发生。

### 统一执行对象

Graph、Chain 和 Workflow 表达连接关系；Compile 后得到 Runnable[I,O]，调用者面对统一的执行接口。I/O 是这段编排的外部类型，不要求每个内部节点都用同一种类型。例如字符串订单号可以经过 Document、金额结构，最终返回字符串摘要。

四种方法按输入输出形态组成二乘二表：Invoke 为单值进、单值出；Stream 为单值进、流出；Collect 为流进、单值出；Transform 为流进、流出。它们不规定网络协议、实时性或性能。内部阶段若需要收齐输入，外部调用 Stream 仍可能等待。

包地图按职责读：schema 定义跨组件数据；components 定义可替换能力；compose 连接与执行；callbacks 观察执行；adk 建立 Agent 循环与事件。供应商实现通常在 eino-ext，调试平台与完整应用示例另有仓库。这个分层是从目录、接口和调用入口归纳的阅读地图，不是动态调用追踪。

源码观察：Runnable 提供四种单值与流之间的输入输出组合。

`compose/runnable.go:28-37`

```
// Runnable is the interface for an executable object. Graph, Chain can be compiled into Runnable.
// runnable is the core conception of eino, we do downgrade compatibility for four data flow patterns,
// and can automatically connect components that only implement one or more methods.
// eg, if a component only implements Stream() method, you can still call Invoke() to convert stream output to invoke output.
type Runnable[I, O any] interface {
	Invoke(ctx context.Context, input I, opts ...Option) (output O, err error)
	Stream(ctx context.Context, input I, opts ...Option) (output *schema.StreamReader[O], err error)
	Collect(ctx context.Context, input *schema.StreamReader[I], opts ...Option) (output O, err error)
	Transform(ctx context.Context, input *schema.StreamReader[I], opts ...Option) (output *schema.StreamReader[O], err error)
}
```

预测：浏览器要逐段显示摘要，应把所有节点都改成 Stream 吗？

参考：先确认输出是否真实增量、哪一层可能 Collect、哪些类型支持拼接，再选择 Runnable.Stream。前端协议由应用定义；把方法名改为 Stream 不保证每层都不缓冲。

### 消息不是纯字符串

一次工具往返至少有三段消息：user 请求；assistant 发出 ToolCalls；tool 返回结果，随后 assistant 再总结。角色说明消息来源，Content 提供可读内容，工具身份字段保持请求与结果的关联。工具消息即使正文相同，也不能只靠文字找到对应请求。

假设模型一次请求两次 sum_order：一张订单 19+23，另一张 8+9。工具名称都一样，ID 才区分这两次调用。结果的 ToolCallID 应对应各自 assistant.ToolCalls 的 ID。丢失 ID 后，内容仍然看起来合理，但下一次模型输入已经破坏协议。

消息可能携带多模态输入、输出和元信息；本课只覆盖文本加标准工具调用。不要将旧 MultiContent 字段当成当前所有多模态类型的唯一入口。需要扩展时从字段注释、Provider 支持和消息拼接规则逐层验证。

源码观察：Message 将工具请求集合与 ToolCallID、ToolName 分开保存。

`schema/message.go:515-525`

```
	Name string `json:"name,omitempty"`

	// only for AssistantMessage
	ToolCalls []ToolCall `json:"tool_calls,omitempty"`

	// only for ToolMessage
	ToolCallID string `json:"tool_call_id,omitempty"`
	// only for ToolMessage
	ToolName string `json:"tool_name,omitempty"`

	ResponseMeta *ResponseMeta `json:"response_meta,omitempty"`
```

预测：两个同名工具调用同时返回 42 和 17，如何正确配对？

参考：通过每次请求的 ID 与结果 ToolCallID 对应，并保留 ToolName。不能按完成时间、金额或名称唯一配对。

### 流的消费与复制

Recv 每次取一个块；io.EOF 表示结束，其他错误表示失败。消费循环要分别处理这两类结果，且在不用时关闭 Reader。Writer 的关闭与 Reader 的关闭责任不同：前者表示不再产生，后者表示下游不再接收。

一个 Reader 不是可以随时重放的数组。若日志回调先读完原流，下游就可能只见 EOF。需要两路消费时使用 Copy(2)，把一个副本交给日志，一个交给下游，并关闭各自持有的副本。原 Reader 在复制后不能继续作为第三路使用。慢消费者可能迫使复制机制保留数据，必须关注内存与取消。

数组 Reader 的验证很轻，但真实 Pipe 会有背压：缓冲满时生产者需要等下游消费。无消费者、忘记关闭、回调读流没有退出，都可能造成卡住。教程实测两个数组副本内容一致；没有把这个结果推广为任意网络流的内存或吞吐保证。

源码观察：Copy 为多个下游提供独立 Reader；n 小于 2 时返回原 Reader。

`schema/stream.go:246-274`

```
// Copy creates n independent StreamReaders that each receive every element of
// the original stream. The original StreamReader becomes unusable after Copy.
//
// Use Copy when two or more pipeline branches need the same stream —
// for example, when a stream must be fed to both a callback handler and the
// next node in a graph:
//
//	copies := sr.Copy(2)
//	sr1, sr2 := copies[0], copies[1]
//	defer sr1.Close()
//	defer sr2.Close()
//
//	// sr1 and sr2 independently read the same elements
//
// n must be at least 1. If n < 2, the original reader is returned unchanged.
func (sr *StreamReader[T]) Copy(n int) []*StreamReader[T] {
	if n < 2 {
		return []*StreamReader[T]{sr}
	}

	if sr.typ == readerTypeArray {
		ret := make([]*StreamReader[T], n)
		for i, ar := range sr.ar.copy(n) {
			ret[i] = &StreamReader[T]{typ: readerTypeArray, ar: ar}
		}
		return ret
	}

	return copyStreamReaders[T](sr, n)
```

预测：加了日志之后业务流为空，第一条诊断假设是什么？

参考：日志和业务可能共同消费了同一个 Reader。确认持有者，给两路分配 Copy(2) 的不同副本；检查 Close 与错误路径。

### 拼接也有不变量

流块可能只包含半段文本或部分工具参数，例如 {"a":19, 与 "b":23}。每块都不一定是合法 JSON；应按消息与工具调用的拼接协议处理后，再进入参数解析阶段。简单地逐块执行工具会把半个参数当成完整请求。

源码会拒绝将不同 ToolCallID 或 ToolName 的块拼成同一消息。这个错误是身份保护，不应为了“继续输出”而吞掉。文本的字符串连接只是拼接规则的一部分；工具调用数组、多模态片段、元信息还各有规则，因此一般不能用 strings.Join 替代框架消息拼接。

诊断时保留：第几个块出错、角色、工具 ID 和类型；不用保存真实个人数据或模型密钥。先构造两个不含敏感内容的冲突块复现，再比较合法块。这样能区分 Provider 输出异常、应用串错两路流和拼接器本身的问题。

源码观察：拼接消息时，非空 ToolCallID 与 ToolName 必须保持一致。

`schema/message.go:1683-1697`

```
		if msg.ToolCallID != "" {
			if ret.ToolCallID == "" {
				ret.ToolCallID = msg.ToolCallID
			} else if ret.ToolCallID != msg.ToolCallID {
				return nil, fmt.Errorf("cannot concat messages with"+
					" different toolCallIDs: '%s' '%s'", ret.ToolCallID, msg.ToolCallID)
			}
		}
		if msg.ToolName != "" {
			if ret.ToolName == "" {
				ret.ToolName = msg.ToolName
			} else if ret.ToolName != msg.ToolName {
				return nil, fmt.Errorf("cannot concat messages with"+
					" different toolNames: '%s' '%s'", ret.ToolCallID, msg.ToolCallID)
			}
```

预测：两个 ToolCallID 不同的块被送到同一拼接器，正确修复是什么？

参考：按正确消息/调用边界分组，修复上游串流或分发错误，再拼接各自的块。不要删掉 ID 使检查失效。

### 显式节点与连边

订单最小图是 START→normalize→report→END。normalize 去掉输入两端空白，report 输出订单摘要。每个节点只负责一个输入输出变换，AddEdge 表达数据与控制的连接。START/END 是框架哨兵，不是你需要注册的普通节点。

Graph[string,string]规定图对外收发字符串，Lambda 内部还有自己的类型。把所有节点包成 any，会将编排期可发现的类型问题推迟到运行时断言。两节点类型不同时，应增加明确转换，或采用受支持的字段映射和合并，并说明转换含义。

本课 playground 的 TestTypedPipeline 使用真实 compose.NewGraph、InvokableLambda、AddEdge、Compile、Invoke。输入“  A-17  ”返回“订单:A-17”；空白输入走业务错误。这里的最小正常链是调试正对照，以后加入模型节点时可先确认图本身仍然连通。

源码观察：NewGraph 的类型参数描述对外边界。

`compose/generic_graph.go:72-85`

```
func NewGraph[I, O any](opts ...NewGraphOption) *Graph[I, O] {
	options := &newGraphOptions{}
	for _, opt := range opts {
		opt(options)
	}

	g := &Graph[I, O]{
		newGraphFromGeneric[I, O](
			ComponentOfGraph,
			options.withState,
			options.stateType,
			opts,
		),
	}
```

预测：图对外输出 string，中间节点返回 int 就一定非法吗？

参考：不一定。若后继明确把 int 转成最终 string，内部异型连接可以成立。非法的是将 int 直接连给要求 string 的节点而没有受支持的转换。

### 两层编译与三类错误

Go 编译器检查你的程序、接口与泛型调用；Eino Compile 检查已经构造的图并返回 Runnable。两层编译解决的问题不同：Go 程序可成功编译，Eino 图仍可能存在不合法的连接、缺失节点或不受支持的结构。

也不能假设所有错误都延迟到 Compile。显式 AddEdge 可立即拒绝 int→string；某些便捷 API 保存 buildError 到后续编译。每次返回 error 的构造方法都要检查，便捷链式方法也要检查最终 Compile。失败之后应重新构造清晰的图，而不是忽略错误继续追加。

执行期错误则来自业务函数、模型、工具、流或上下文取消。TestBadEdgeRejected 实测错误指出 length 输出 int 与 text 输入 string 不匹配；TestTypedPipeline 的 empty order 是运行期业务错误。把它们放在不同日志阶段，能快速判断应该修改图，还是修改输入与业务规则。

源码观察：Compile 构造编译选项，调用内部图编译并传播错误。

`compose/generic_graph.go:123-136`

```
func (g *Graph[I, O]) Compile(ctx context.Context, opts ...GraphCompileOption) (Runnable[I, O], error) {
	return compileAnyGraph[I, O](ctx, g, opts...)
}

func compileAnyGraph[I, O any](ctx context.Context, g AnyGraph, opts ...GraphCompileOption) (Runnable[I, O], error) {
	if len(globalGraphCompileCallbacks) > 0 {
		opts = append([]GraphCompileOption{WithGraphCompileCallbacks(globalGraphCompileCallbacks...)}, opts...)
	}
	option := newGraphCompileOptions(opts...)

	cr, err := g.compile(ctx, option)
	if err != nil {
		return nil, err
	}
```

预测：应用已经构建成功，但 AddEdge 报类型不匹配，能靠重试 Invoke 解决吗？

参考：不能。错误发生在编排构造阶段；需要修正节点签名或加入转换，并重新编译图。重试适合特定暂时性运行故障，不适合确定的结构错误。

### 编译后冻结结构

图编译后会使用稳定的节点和边关系。源码显式拒绝在已编译的图上继续新增节点；实测也验证新增边返回 ErrGraphCompiled。不要把一个已共享给多个请求的图当成每次请求都能原地增删工具的可变对象。

Chain 适合明显的顺序流程，Compile 会补 END 边再委托底层 Graph；Graph 适合分支、循环与显式结构；Workflow 强调依赖组织与字段映射。三者共享执行抽象，但构造便利性、触发方式和可表达结构需要分别看当前实现。

正确迁移方法是先冻结最小输入输出与失败契约，选择最简构造 API，然后用相同样例检验结果。只有遇到真实需要的路由、循环或字段依赖，再提升为更一般的图。更多节点和更复杂的抽象本身不会提高任务质量。

源码观察：编译后的图拒绝新增节点，START/END 名称保留。

`compose/graph.go:162-178`

```
func (g *graph) addNode(key string, node *graphNode, options *graphAddNodeOpts) (err error) {
	if g.buildError != nil {
		return g.buildError
	}

	if g.compiled {
		return ErrGraphCompiled
	}

	defer func() {
		if err != nil {
			g.buildError = err
		}
	}()

	if key == END || key == START {
		return fmt.Errorf("node '%s' is reserved, cannot add manually", key)
```

预测：想给已编译图加一个审计节点，应怎么做？

参考：构建一个包含审计节点的新图，检查所有构造错误，重新 Compile 并回归正常、空输入和类型错误样例。不要原地修改已共享 Runnable 的结构。

### 分支返回下一步身份

“订单已知就读取，否则进入人工复核”是一个控制选择。我们的 route 节点输出原输入；条件函数根据 known 前缀返回 local 或 review；两个目标再通向 END。分支返回的是节点 key，而不是最终业务结果，也不是用户看到的文字。

构造分支时声明可达目标集合，可以约束运行期的选择。条件函数的输入类型必须匹配分支源的输出。返回未声明或不存在的目标属于编排/路由错误；不要默认未知返回值会自动落入安全的兜底路径。应用应显式设计 review 之类的合法兜底。

实测 known-A→local:known-A，unknown-B→review:unknown-B。这个验证只说明确定性路由与两个目标连接成立；没有运行模型分类，也没有证明业务上“已知订单”的判定正确。将条件换成模型时，应保留这两条冻结样例并增加不合法路由输出案例。

源码观察：单目标分支把条件返回的节点名转换为多目标集合。

`compose/branch.go:145-152`

```
func NewGraphBranch[T any](condition GraphBranchCondition[T], endNodes map[string]bool) *GraphBranch {
	return NewGraphMultiBranch(func(ctx context.Context, in T) (endNode map[string]bool, err error) {
		ret, err := condition(ctx, in)
		if err != nil {
			return nil, err
		}
		return map[string]bool{ret: true}, nil
	}, endNodes)
```

预测：分支函数返回 review，但 END 没收到结果，应检查哪些连接？

参考：先检查 review 已声明且注册，源节点类型与条件类型一致，再检查 review→END 边及 review 执行错误。不能只看 condition 返回了字符串。

### 触发模式与 eager 不混用

AnyPredecessor 关注前一已完成 superstep 中任一前驱；AllPredecessor 要等所有前驱完成。不能把二者概括成“所有图都是等待全部上游”。一个有环 Agent 流程和一个静态依赖 DAG，常有不同触发需求。

当前版本 AllPredecessor Graph 与 Workflow 默认 eager：节点就绪即可执行，不必等整轮 superstep 结束。WithEagerExecution 已废弃且为空操作；需要旧的屏障等待行为时看 WithEagerExecutionDisabled。旧教程给出的选项名不一定还代表一次有效配置变更。

触发与数据合并是两件事：节点满足运行条件，不代表多个上游返回同类型数据就自动按业务语义合并。多路金额如何加总、失败是否短路、是否需要所有订单到齐，应在输入映射/合并与错误策略中明确。教程没有跑并发压力或复杂 fan-in；此段是源码观察。

源码观察：Graph 默认 AnyPredecessor；AllPredecessor/Workflow 默认 eager，可禁用。

`compose/graph_compile_options.go:84-101`

```
// WithEagerExecutionDisabled disables the eager execution mode for the graph.
// By default, eager execution is enabled for Workflow and Graph with the AllPredecessor trigger mode.
// After using this option, nodes will wait for the completion of a super step instead of execute immediately once they are ready to run.
// ref: https://www.cloudwego.io/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/#runtime-engine
func WithEagerExecutionDisabled() GraphCompileOption {
	return func(o *graphCompileOptions) {
		o.eagerDisabled = true
	}
}

// WithNodeTriggerMode sets the trigger mode for nodes in the graph.
// The trigger mode determines when a node is triggered during graph execution, ref: https://www.cloudwego.io/docs/eino/core_modules/chain_and_graph_orchestration/orchestration_design_principles/#runtime-engine
// AnyPredecessor by default.
func WithNodeTriggerMode(triggerMode NodeTriggerMode) GraphCompileOption {
	return func(o *graphCompileOptions) {
		o.nodeTriggerMode = triggerMode
	}
}
```

预测：一个节点已满足所有前驱条件，为何会在同轮另一节点结束前运行？

参考：当前 AllPredecessor/Workflow 默认 eager，只需本节点依赖就绪。若业务要求整轮屏障，检查 WithEagerExecutionDisabled，并评估是否真的需要该顺序。

### 状态工厂与受锁访问

有些信息不适合每条边都传：处理计数、局部缓存、审计标签。WithGenLocalState 接收工厂，为每次运行生成状态；ProcessState 从当前上下文找到相应类型并在锁内处理。若多个运行都返回同一个全局指针，工厂就失去了隔离意义。

锁只保护 handler 中的访问；在外部保留状态指针或另开 goroutine，不能自动得到同样保护。在锁内再次调用同一状态的 ProcessState 可能自锁，慢网络请求也会让其他节点等待。可以先取快照并释放锁，再执行外部操作，最后按明确规则更新。

图局部状态、ADK 一次运行的消息状态、session 值、持久 checkpoint、业务订单记录各有边界。恢复旧状态需要序列化与存储契约，跨用户共享需要应用身份规则。单看 ProcessState 的互斥锁，不能推导这些跨运行与跨用户保证。

源码观察：ProcessState 查找状态，在互斥锁内执行 handler；没有状态则返回错误。

`compose/state.go:165-180`

```
func ProcessState[S any](ctx context.Context, handler func(context.Context, S) error) error {
	s, pMu, err := getState[S](ctx)
	if err != nil {
		return fmt.Errorf("get state from context fail: %w", err)
	}
	pMu.Lock()
	defer pMu.Unlock()
	return handler(ctx, s)
}

func getState[S any](ctx context.Context) (S, *sync.Mutex, error) {
	state := ctx.Value(stateKey{})

	if state == nil {
		var s S
		return s, nil, fmt.Errorf("have not set state")
```

预测：两个用户的图运行意外共享同一计数器，首先查看什么？

参考：检查 WithGenLocalState 的工厂是否每次都返回同一个全局指针，然后检查 handler 外的别名访问。每次创建新状态并通过受锁入口更新；持久共享若是业务需求，应另建明确存储层。

### 结构描述与解析的边界

工具接口有三层：Info 告诉模型能调用什么；参数 schema 描述输入形状；执行方法把输入变成结果。InferTool 可以根据 Go 结构生成元信息并包装函数，减少重复编解码；它不能替你决定金额单位、退款政策或所有权。

源码默认将 JSON 反序列化为 T。成功反序列化不等于所有业务约束已验证，例如缺少数值字段常得到零值，负金额仍可能是合法整数，无法仅靠 JSON 解码区分“未提供”和“明确为零”。必要时使用指针字段、显式校验和业务错误类型。

本课 sumTool 故意使用手写 Info 和 JSON 解析，让描述与执行的边界可见。脚本模型预先知道参数，不依赖 schema 诱导生成，所以测试没有证明 schema 的模型可用性。真实 Provider 必须再验证参数描述、required、枚举、多模态结果以及 tools 请求选项支持。

源码观察：InvokableRun 使用自定义解码或 Sonic JSON 解码得到类型 T。

`components/tool/utils/invokable_func.go:173-195`

```
// InvokableRun invokes the tool with the given arguments.
func (i *invokableTool[T, D]) InvokableRun(ctx context.Context, arguments string, opts ...tool.Option) (output string, err error) {

	var inst T
	if i.um != nil {
		var val any
		val, err = i.um(ctx, arguments)
		if err != nil {
			return "", fmt.Errorf("[LocalFunc] failed to unmarshal arguments, toolName=%s, err=%w", i.getToolName(), err)
		}
		gt, ok := val.(T)
		if !ok {
			return "", fmt.Errorf("[LocalFunc] invalid type, toolName=%s, expected=%T, given=%T", i.getToolName(), inst, val)
		}
		inst = gt
	} else {
		inst = generic.NewInstance[T]()

		err = sonic.UnmarshalString(arguments, &inst)
		if err != nil {
			return "", fmt.Errorf("[LocalFunc] failed to unmarshal arguments in json, toolName=%s, err=%w", i.getToolName(), err)
		}
	}
```

预测：JSON 解码成功但金额是负数，应该在哪修复？

参考：在工具业务入口或专门校验层拒绝不合法金额，并定义单位/范围。schema 可以帮助约束生成，但成功解码不能取代业务校验。

### 注册与未知工具

ToolsNode 建立工具名称到可执行入口的索引，并把 assistant.ToolCalls 转成任务。调用前应确认名称指向当前授权的能力。未知工具在没有 UnknownToolsHandler 时失败；配置自定义处理器会改变这条行为，不能把教程的默认断言推广到所有配置。

默认可以并发运行工具，配置 executeSequentially 时顺序运行。并发的价值是减少互相独立任务的等待；若两个调用修改同一订单，仍需业务事务、锁或显式依赖。结果列表关联请求身份，不等于外部写入天然安全或可回滚。

实测先执行 sum_order 得到 42，再将名称改成 unknown。后一请求被拒绝，工具调用计数保持 1。这验证了默认注册表拒绝路径；没有证明所有恶意参数或越权请求都被拒绝。不要把“在名单里”当成“当前用户可以做任何事情”。

源码观察：工具按名称索引分发；未注册且无 UnknownToolsHandler 时返回错误。

`compose/tool_node.go:925-934`

```
		index, ok := tuple.indexes[toolCall.Function.Name]
		if !ok {
			if tn.unknownToolHandler == nil {
				return nil, fmt.Errorf("tool %s not found in toolsNode indexes", toolCall.Function.Name)
			}
			toolCallTasks[i] = newUnknownToolTask(toolCall.Function.Name, toolCall.Function.Arguments, toolCall.ID, tn.unknownToolHandler)
		} else {
			toolCallTasks[i].meta = tuple.meta[index]
			toolCallTasks[i].name = toolCall.Function.Name
			toolCallTasks[i].callID = toolCall.ID
```

预测：未知工具突然不再报错，应该先检查哪项配置？

参考：检查 UnknownToolsHandler 是否设置，以及 ToolList/别名/本次调用选项是否改变了分发集合。先重建有效注册表，不应认定框架忽略了错误。

### 结果身份与重复副作用

本地函数返回字符串后，框架才把它封装成 tool 消息，带上任务的调用 ID 和名称。模型下一轮因此能把“42”与自己刚请求的计算对应。标准文本工具和增强多模态工具的结果结构不同，源码在这里分别处理。

ToolCallID 是协议关联身份，不天然是数据库幂等键。工具已经付款成功、响应还没送到模型就进程崩溃，重跑可能再次付款；即使 checkpoint 记录了部分已执行工具，持久化时序和业务系统也需要证明。对写工具，应由应用明确稳定幂等键、事务结果查询和失败恢复策略。

排错顺序：请求 ID→注册工具→参数→执行返回值→ToolMessage→下一轮模型输入。若最终答案错，不要直接归因“模型幻觉”：可能根本没执行，可能金额单位错，可能结果 ID 错配，也可能模型没有正确使用合法工具结果。

源码观察：标准结果用任务的 callID 和名称构造 ToolMessage。

`compose/tool_node.go:1232-1241`

```
		if len(errs) == 0 {
			if tasks[i].useEnhanced {
				output[i] = schema.ToolMessage("", tasks[i].callID, schema.WithToolName(tasks[i].name))
				output[i].UserInputMultiContent, err = tasks[i].enhancedOutput.ToMessageInputParts()
				if err != nil {
					return nil, err
				}
			} else {
				output[i] = schema.ToolMessage(tasks[i].output, tasks[i].callID, schema.WithToolName(tasks[i].name))
			}
```

预测：工具已写入成功但最终事件丢失，可以直接重跑整个 Agent 吗？

参考：先查询业务写入结果并使用幂等策略；明确恢复位置与已执行记录，再决定重试范围。仅凭 ToolCallID 或 UI 没显示不能证明工具未执行。

### Runner 管一次执行与事件

Runner 接入 Agent，配置流式模式和可选 CheckPointStore；Query 是快捷入口，把一个字符串变成 user 消息后调用 Run。它不是自动把所有过往 Query 加进聊天历史的数据库。要继续普通对话，应用应明确管理消息列表；恢复中断则使用 Resume 系列入口。

Run 返回 AsyncIterator，逐个读取事件。事件可包含输出、Action 或 Err，因此没有正文的工具请求和控制事件也可能有意义。只取最后一个 Content 字段会漏掉工具事件、错误和中断。示例完整迭代到结束，遇到 Err 就失败，并读取 Output.MessageOutput。

若 EnableStreaming 为真，MessageOutput 可能持有流；GetMessage 会消费并拼成完整消息，适合完整展示但失去逐块可见性。要流式 UI，需要正确消费 MessageStream、处理 EOF 与错误，再定义应用传输协议。Runner 自己不提供网页连接、HTTP 认证或浏览器重连。

源码观察：Query 构造一条 user 消息并调用 Run，开始新执行。

`adk/runner.go:102-115`

```
func (r *TypedRunner[M]) Run(ctx context.Context, messages []M,
	opts ...AgentRunOption) *AsyncIterator[*TypedAgentEvent[M]] {
	return typedRunnerRunImpl(r.a, r.enableStreaming, r.store, ctx, messages, opts...)
}

// Query is a convenience method that starts a new execution with a single user query string.
func (r *TypedRunner[M]) Query(ctx context.Context,
	query string, opts ...AgentRunOption) *AsyncIterator[*TypedAgentEvent[M]] {
	msgs, err := newUserMessage[M](query)
	if err != nil {
		return errorIterator[M](err)
	}
	return r.Run(ctx, []M{msgs}, opts...)
}
```

预测：连续调用两次 Query，第二次一定能看到第一次对话吗？

参考：不能从 Query 的契约得出这一点。它开始只有一条 user 消息的新执行；普通历史需由应用管理后传给 Run，中断恢复则另走 checkpoint。

### ChatModelAgent 的工具分支与迭代上限

ChatModelAgent 将指令、消息、工具配置和模型组织成执行行为。有工具时走 ReAct，无工具时走较直接的模型流程。它让“模型请求工具→工具结果追加→模型再次生成”成为可驱动的闭环；选择能力和判断结果仍依赖具体模型与应用。

当前版本通过 model.WithTools 调用选项传递工具信息，配置字段接受 BaseModel。不要机械要求所有接入模型必须实现旧 BindTools。另一个 ToolCallingChatModel.WithTools 接口强调返回新实例的安全绑定，两种同名机制的层次不同。

MaxIterations 是模型生成周期上限，不是工具调用数、token 预算或时间期限。一次模型生成可发多条 ToolCalls；一次工具结果后也可能继续发新调用。因此即使 MaxIterations=3，也不能据此断言最多三次工具执行或固定费用。模型 token 限制、上下文取消、工具超时应分别配置。

源码观察：配置要求模型支持请求级 tools 选项；MaxIterations 限制模型生成周期，默认 20。

`adk/chatmodel.go:277-308`

```
	// Model is the chat model used by the agent.
	// If your ChatModelAgent uses any tools, this model must support the model.WithTools
	// call option, as that's how ChatModelAgent configures the model with tool information.
	Model model.BaseModel[M]

	ToolsConfig ToolsConfig

	// GenModelInput transforms instructions and input messages into the model's input format.
	// Optional. Defaults to defaultGenModelInput which combines instruction and messages.
	GenModelInput TypedGenModelInput[M]

	// Exit defines the tool used to terminate the agent process.
	// Optional. If nil, no Exit Action will be generated.
	// You can use the provided 'ExitTool' implementation directly.
	//
	// NOT RECOMMENDED: Agent transfer with full context sharing between agents has not proven
	// to be more effective empirically. Consider using ChatModelAgent with AgentTool
	// or DeepAgent instead for most multi-agent scenarios.
	Exit tool.BaseTool

	// OutputKey stores the agent's response in the session.
	// Optional. When set, stores output via AddSessionValue(ctx, outputKey, msg.Content).
	//
	// NOT RECOMMENDED: Agent transfer with full context sharing between agents has not proven
	// to be more effective empirically. Consider using ChatModelAgent with AgentTool
	// or DeepAgent instead for most multi-agent scenarios.
	OutputKey string

	// MaxIterations defines the upper limit of ChatModel generation cycles.
	// The agent will terminate with an error if this limit is exceeded.
	// Optional. Defaults to 20.
	MaxIterations int
```

预测：一次模型生成请求四个工具，MaxIterations=3 是否违反上限？

参考：仅这一轮不违反模型生成周期上限；工具数不能直接替换为迭代数。但具体配置还可能有其他工具、时间或业务限制。

### 把 Agent 当工具而不是全量转交

当订单 Agent 需要税费专家时，可以把专家 Agent 包成工具：父 Agent 给一个局部 request，拿回结果后继续原任务。默认 request 参数是清晰的输入边界；WithFullChatHistoryAsInput 显式扩大上下文范围。这个选项的存在提醒我们，子能力并不天然需要全部历史。

AgentTool、agent transfer 与预置 DeepAgent 是不同组织方式。当前源码对全上下文 transfer 的有效性有保留注释；这属于源码方观点，不是本课实验结论。教程以最小父 Agent 工具循环为主，不宣称跑过多 Agent、文件系统中间件或真实子任务。

实测脚本模型两次 Generate：第一次给 sum_order 参数，第二次收到 tool 结果后给最终答案；工具只执行一次，收到三个事件。这证明框架闭环、事件和工具关联路径可工作。脚本模型预设了正确路线，所以它不测自然语言理解、工具选择质量和复杂问题解决能力。

源码观察：AgentTool 默认输入描述为 request，可显式开启全量历史或自定义 schema。

`adk/agent_tool.go:32-60`

```
var (
	defaultAgentToolParam = schema.NewParamsOneOfByParams(map[string]*schema.ParameterInfo{
		"request": {
			Desc:     "request to be processed",
			Required: true,
			Type:     schema.String,
		},
	})
)

type AgentToolOptions struct {
	fullChatHistoryAsInput bool
	agentInputSchema       *schema.ParamsOneOf
}

type AgentToolOption func(*AgentToolOptions)

// WithFullChatHistoryAsInput enables using the full chat history as input.
func WithFullChatHistoryAsInput() AgentToolOption {
	return func(options *AgentToolOptions) {
		options.fullChatHistoryAsInput = true
	}
}

// WithAgentInputSchema sets a custom input schema for the agent tool.
func WithAgentInputSchema(schema *schema.ParamsOneOf) AgentToolOption {
	return func(options *AgentToolOptions) {
		options.agentInputSchema = schema
	}
```

预测：税费专家只需订单金额，是否应默认给它整个用户聊天历史？

参考：先给完成子任务所需的最小请求与参数，明确输出契约；只有必要且授权时扩大到全历史。再独立评估信息充足性与数据边界。

### 存储接口不等于持久性保证

检查点保存“从哪里继续、哪些中断点、哪些状态”的必要信息。Store 只规定按 ID 读写字节。内存实现可验证接口，却不能在进程退出后保留；文件、数据库、对象存储需要独立验证一致性、容量、加密和生命周期。

ADK Runner 的 CheckPointStore 与 compose 的检查点选项是各自公开入口，内部共享一些核心机制，但调用层不能随意混用。需要给一次执行明确 CheckPointID，并提供可用存储；仅写入一个同名字符串并不自动创建可恢复状态。

Store.Get 返回 bytes、是否存在和 error。找不到不是空白消息；读取失败也不能当不存在。可选 Delete 不保证任何存储都自动清理，注释明确提醒 TTL 或外部清理属于存储拥有者的责任。本课没有运行重启恢复或存储故障注入，后续应针对选定实现另立基准。

源码观察：CheckPointStore 要求 Get/Set；可选 Deleter 提供显式删除，生命周期由存储拥有者管理。

`internal/core/interrupt.go:31-44`

```
type CheckPointStore interface {
	Get(ctx context.Context, checkPointID string) ([]byte, bool, error)
	Set(ctx context.Context, checkPointID string, checkPoint []byte) error
}

// CheckPointDeleter is an optional interface that CheckPointStore implementations
// can implement to support explicit checkpoint deletion.
//
// If the Store does not implement this interface, stale checkpoints will NOT be
// automatically cleaned up. The store owner is responsible for managing checkpoint
// lifecycle in that case (e.g., via TTL, external cleanup, or implementing this
// interface).
type CheckPointDeleter interface {
	Delete(ctx context.Context, checkPointID string) error
```

预测：内存 Store 可以 Set/Get，能否证明进程重启后能恢复？

参考：不能。需要选定持久实现，在独立进程写入、退出、读取并恢复，同时验证版本、数据完整性与副作用行为。

### 恢复目标与恢复数据

中断不是把函数睡眠到明天；执行返回中断事件，框架保留继续所需状态，外部收到确认或新信息后再调用恢复。Resume 是隐式全部继续的简化入口；ResumeWithParams 用 Targets 精确指定哪些地址获得什么恢复数据。

地址识别中断层级里的具体组件，ResumeData 是该组件期待的数据。若两个工具分别等“允许查询订单”和“允许退款”，不能把一个 true 自动扩散成所有操作授权。未命中的叶子中断点需要保留状态并再次中断；复合 Agent 负责把信号传给下游。

应用仍需验证批准者、时间、范围和对象，将外部批准映射到合法地址与数据。框架提供中断/恢复结构，不自动决定批准是否足够或是否过期。断网、取消、业务错误与人为中断也不是同义状态，必须按实际事件分类。

源码观察：ResumeWithParams 使用地址到数据的 Targets，未命中的叶子中断点应再次中断。

`adk/runner.go:129-148`

```
// ResumeWithParams continues an interrupted execution from a checkpoint with specific parameters.
// This is the most common and powerful way to resume, allowing you to target specific interrupt points
// (identified by their address/ID) and provide them with data.
//
// The params.Targets map should contain the addresses of the components to be resumed as keys. These addresses
// can point to any interruptible component in the entire execution graph, including ADK agents, compose
// graph nodes, or tools. The value can be the resume data for that component, or `nil` if no data is needed.
//
// When using this method:
//   - Components whose addresses are in the params.Targets map will receive `isResumeFlow = true` when they
//     call `GetResumeContext`.
//   - Interrupted components whose addresses are NOT in the params.Targets map must decide how to proceed:
//     -- "Leaf" components (the actual root causes of the original interrupt) MUST re-interrupt themselves
//     to preserve their state.
//     -- "Composite" agents (like SequentialAgent or ChatModelAgent) should generally proceed with their
//     execution. They act as conduits, allowing the resume signal to flow to their children. They will
//     naturally re-interrupt if one of their interrupted children re-interrupts, as they receive the
//     new `CompositeInterrupt` signal from them.
func (r *TypedRunner[M]) ResumeWithParams(ctx context.Context, checkPointID string, params *ResumeParams, opts ...AgentRunOption) (*AsyncIterator[*TypedAgentEvent[M]], error) {
	return r.resumeInternal(ctx, checkPointID, params.Targets, opts...)
```

预测：两个工具在等不同确认，只批准其中一个，应调用什么并检查什么？

参考：使用 ResumeWithParams 给指定中断地址提供合法数据；确认另一个叶子仍中断，且应用已验证批准身份与范围。不能用一个全局布尔值批准全部。

### 恢复失败的三道门

加载路径给出自然排错顺序：Store.Get 是否成功且 existed；checkpoint 字节是否能 gob 解码；框架状态能否恢复；最后才进入继续执行。把“ID 不存在”与“字节版本不兼容”都记成模型失败，会丢掉最关键的定位信息。

当前实现带有旧检查点格式兼容处理，源码中可见 preprocess 与类型注册。兼容代码存在不能证明你的所有自定义状态、Provider 变化或跨版本快照都能恢复。自定义状态中接口字段的实际类型、不可序列化对象和版本变更需要固定样例。

更困难的是副作用窗口：工具已完成而 checkpoint 未落盘，或者 checkpoint 保存后外部结果仍未确定。恢复时应结合业务幂等与结果查询。此章节所有恢复行为来自源码读取，六个已运行测试没有覆盖这里；这条证据边界在课程、讲义和验收里保持一致。

源码观察：加载先检查存储存在，再解码，再恢复 checkpoint 数据与中断状态。

`adk/interrupt.go:223-248`

```
func runnerLoadCheckPointImpl(store CheckPointStore, ctx context.Context, checkpointID string) (
	context.Context, *runContext, *ResumeInfo, error) {
	data, existed, err := store.Get(ctx, checkpointID)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("failed to get checkpoint from store: %w", err)
	}
	if !existed {
		return nil, nil, nil, fmt.Errorf("checkpoint[%s] not exist", checkpointID)
	}

	data = preprocessADKCheckpoint(data)

	s := &serialization{}
	err = gob.NewDecoder(bytes.NewReader(data)).Decode(s)
	if err != nil {
		return nil, nil, nil, fmt.Errorf("failed to decode checkpoint: %w", err)
	}
	if err = restoreRunnerCheckpointInfoData(s); err != nil {
		return nil, nil, nil, err
	}
	ctx = core.PopulateInterruptState(ctx, s.InterruptID2Address, s.InterruptID2State)

	return ctx, s.RunCtx, &ResumeInfo{
		EnableStreaming: s.EnableStreaming,
		InterruptInfo:   s.Info,
	}, nil
```

预测：恢复报 failed to decode checkpoint，先重跑模型能解决吗？

参考：先冻结失败字节与元数据，核对 checkpoint schema、版本和注册类型，复现解码；不可把不兼容数据当新任务悄悄重跑，尤其涉及写工具时。

### 回调观察也有流边界

callbacks 沿执行边界提供观察入口，不能直接判定业务结果正确。记录节点名称/组件类型、开始结束、错误和必要身份，再按阶段排查：是否生成、是否找到工具、参数或流是否失败、是否达到上限，以及是否被用户取消。

流回调与单值回调不同。若为调试而把整段流收集后打印，可能改变延迟和内存行为；若错误地共享 Reader，还会影响业务消费。选择需要的字段，保留身份与阶段，避免日志里存真实密钥、个人数据和完整私有上下文。

本课没有增加全局追踪平台或验证 callback 的所有时序。它提供接口锚点与排错表，让你在本地最小图中先加一层轻量观测，记录是否改变输出、调用数与流消费。观测自身的无干扰性也应有行为对照。

源码观察：Handler 提供开始、结束、错误以及流输入/输出回调。

`internal/callbacks/interface.go:38-48`

```
type Handler interface {
	OnStart(ctx context.Context, info *RunInfo, input CallbackInput) context.Context
	OnEnd(ctx context.Context, info *RunInfo, output CallbackOutput) context.Context

	OnError(ctx context.Context, info *RunInfo, err error) context.Context

	OnStartWithStreamInput(ctx context.Context, info *RunInfo,
		input *schema.StreamReader[CallbackInput]) context.Context
	OnEndWithStreamOutput(ctx context.Context, info *RunInfo,
		output *schema.StreamReader[CallbackOutput]) context.Context
}
```

预测：加回调后流式延迟显著增加，怎样验证是否是观测导致？

参考：用相同输入对比关闭与启用回调，检查是否 Collect 完整流或阻塞消费；保留输出一致性、首块时间和结束时间，再优化必要字段与复制策略。

### 生成与消费事件不要混为一谈

阅读最终答案之前，先阅读验证日志：六个 PASS 各有明确样例与断言。类型链覆盖正常、空输入与编译后修改拒绝；分支覆盖两条路线；不合法边覆盖类型失败；流覆盖副本与 Stream→Invoke；ToolsNode 覆盖 ID 与 unknown；ADK 覆盖两次模型、一次工具、三个事件。

运行的是固定 revision 的真实 Eino 包，脚本模型和本地工具是替身。因此“真实库执行”与“真实模型推理”可以分别成立或未测。Sonic 在 Go 1.27.1 上报告不支持该快路径并回退标准 JSON；示例结果通过，但不能宣称测得 Sonic 性能或最低 Go 版本兼容。

开始自己的学习记录时，请先写预测再运行。看过答案、网页完成进度、作者参考测试通过，都不能记录为你掌握了概念。课程只保存浏览器草稿；评估必须依据你给出的因果解释、正确定位和新场景迁移。

源码观察：GetMessage 在 streaming 模式会拼接并消费 MessageStream。

`adk/interface.go:100-105`

```
func (mv *TypedMessageVariant[M]) GetMessage() (M, error) {
	if mv.IsStreaming {
		return concatMessageStream(mv.MessageStream)
	}
	return mv.Message, nil
}
```

预测：看到六个 PASS，能否把 checkpoint、MCP 和学习掌握都标为通过？

参考：不能。逐项对照测试范围；checkpoint/MCP 没有被执行，学习掌握需独立评估真实回答。参考运行只证明其断言对应的框架行为。

### 先冻结可比较的扩展

迁移到“读取两个报价、比较价格、生成采购摘要”时，保持同样的骨架：类型化输入→合法路由→只读工具→结果身份→模型或模板摘要→事件消费。变化的首先是参数、单位、权限和失败规则，而不是先选一个更复杂 Agent 名称。

推荐下一步局部重建 stream 拼接与身份校验，边界只包括文本块、EOF、错误与冲突 ToolCallID。先写正常拼接、两路复制、身份冲突、提前取消的行为契约，再独立实现小核心与真实 Eino 比较。这个重建尚未交付，不把阅读课伪装成完整框架复刻。

受控扩展候选是工具加入 currency 和 amount_minor，冻结币种与最小单位、缺字段、负数、未知币种、重复 ID 和正常路径。增加结构描述、解码后业务校验和结果格式，再跑原六个回归与新增契约。最后复述哪个问题由类型负责、哪个由运行时负责、哪个仍由业务负责。

源码观察：Runnable 的输入输出边界适合定义局部替代与迁移的行为契约。

`compose/runnable.go:32-37`

```
type Runnable[I, O any] interface {
	Invoke(ctx context.Context, input I, opts ...Option) (output O, err error)
	Stream(ctx context.Context, input I, opts ...Option) (output *schema.StreamReader[O], err error)
	Collect(ctx context.Context, input *schema.StreamReader[I], opts ...Option) (output O, err error)
	Transform(ctx context.Context, input *schema.StreamReader[I], opts ...Option) (output *schema.StreamReader[O], err error)
}
```

预测：将订单工具换成报价比较，第一份规格应冻结哪些内容？

参考：冻结输入/输出类型、币种和单位、只读权限、来源时间、ID 关联、错误与超时行为，以及正常/非法/重复样例。保持原循环正对照后再测试真实 Provider。

### 闭卷复述与迁移

把类型链、工具循环和恢复分别归入已运行或静态观察，并说明各自能够证明什么。

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## OpenHands Agent SDK · Conversation 与事件账本

Conversation 与事件账本

来源：https://github.com/OpenHands/software-agent-sdk

提交：`004c674a96d7eeeba70fcefc0e6dfc6a87958d3d`；访问：2026-10-02

证据：独立教学模型3组固定正/错误策略对照；不导入上游，不构成生产Runtime验证。

本章覆盖 SDK，不等于整个 OpenHands 产品；鉴权、远程执行与隔离未运行。

排除：真实模型与供应商质量；真实沙箱/鉴权与部署；跨进程持久恢复及外部副作用恰好一次；并发压力与生产竞态；学习者实际作答及掌握度

### 本案例阅读任务

沿 Conversation、Agent.step 和事件账本追踪任务，解释消息接纳、执行和发布的先后关系。

读前准备：第 1、2、6 章；能阅读 Python 异步调用。Workspace 表示具体的执行环境。

1. 区分 send_message 接纳输入与 run 启动执行。
2. 追 Action、Observation 及保存后发布的事件路径。
3. 核对 HEAD、暂停和 fork，再检查工作区副作用是否与事件同步。

检验理解：事件历史已恢复，但工作区文件不同，为什么不能称为完整恢复？

判断标准：说明活动事件分支只能重建推理视图；文件和远程操作需要额外的工作区快照或恢复证据。

阅读主线：沿 Conversation、Agent.step、工具执行、Workspace 与事件持久化，理解运行责任。

### Conversation 是应用控制面

示例建立 Agent、工具、Workspace 与 Conversation，再发送消息并启动运行。入口的这些对象分别决定推理、行动能力、执行位置与任务状态。

本课程范围是 software-agent-sdk 仓库，不等于整个 OpenHands 平台。网页产品、部署、Canvas 与 SDK 的边界应分开；一个 hello world 不能证明远程服务已经可用。

源码观察：白话翻译
        Agent 先拿到模型与工具规格，Conversation 再绑定当前目录。消息进入会话后，显式的 run() 才启动执行。

`examples/01_standalone_sdk/01_hello_world.py:15-28`

```
agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

cwd = os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)

conversation.send_message("Write 3 facts about the current project into FACTS.txt.")
conversation.run()
```

预测：SDK 示例跑通就证明整个平台部署完成吗？

参考：不能。确认示例使用的 Conversation 和 Workspace 类型；SDK、Agent Server 与完整平台分别验收。

### send_message 与 run 分开

send_message 接纳用户消息，并将 FINISHED/STUCK 等状态转为可再次运行的 IDLE。模型生成由后续 run 驱动，所以排查无响应时先确认两步是否都发生。

输入排队、开始执行、收到事件、结束一轮属于四个时间点。调用者若只 send 不 run，可能只得到持久化消息；反过来多个发送与运行并发需要遵守状态与锁契约。

源码观察：白话翻译
        字符串被包装成唯一允许进入该 API 的 user Message。新消息会把 FINISHED / STUCK 重置为 IDLE，但还没有调用 LLM。

`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:1826-1839`

```
        if isinstance(message, str):
            message = Message(role="user", content=[TextContent(text=message)])

        assert message.role == "user", (
            "Only user messages are allowed to be sent to the agent."
        )
        with self._state:
            if self._state.execution_status in (
                ConversationExecutionStatus.FINISHED,
                ConversationExecutionStatus.STUCK,
            ):
                self._state.execution_status = (
                    ConversationExecutionStatus.IDLE
                )  # new message resets terminal states
```

预测：发送成功但没有assistant事件，先检查什么？

参考：确认是否调用 run/远程调度、当前状态和队列；send_message只加入消息，不能直接证明模型调用已发生。

### 用户消息也有事件身份

用户输入被包装为 MessageEvent，包含来源与内容，并走统一事件回调路径。事件身份提供追踪入口，知识附加与 sender 信息也影响后续上下文。

不要把界面上的一行文字当完整消息协议。调查串会话时，关联 conversation ID、event ID 与父关系，再看渲染；UI 内容相同不代表事件相同。

源码观察：白话翻译
        准备好的消息被包装成 MessageEvent，再进入统一 callback；可选的知识扩展与 sender 也一同记录。

`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:1863-1870`

```
            user_msg_event = MessageEvent(
                source="user",
                llm_message=message,
                activated_skills=activated_skill_names,
                extended_content=extended_content,
                sender=sender,
            )
            self._on_event(user_msg_event)
```

预测：两次相同正文的用户消息如何区分？

参考：靠事件ID、所属Conversation和父关系，而不是正文字符串；重复文本也可能是不同轮次。

### 先保存再发布

本地主线先将事件 append 到状态/存储，再经 PubSub 和回调通知观察者。可视化异常不应改变已经保存的事实。

先保存再通知，可以减少 UI 已显示而账本尚未记录的窗口。不过 append 成功仍不足以证明所有订阅者收到事件；断线、回调失败和重放需要单独检查，不能据此推导 exactly once。

源码观察：白话翻译
        每个 Event 都先交给 append_event。如果持久化失败，排在后面的 PubSub / 用户 callback 不会收到这条未落盘事件；本地终端 visualizer 是例外，但它不构成客户端可依赖的通知。

`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:415-438`

```
        # Default callback: persist every event to state
        def _default_callback(e):
            # This callback runs while holding the conversation state's lock
            # (see BaseConversation.compose_callbacks usage inside `with self._state:`
            # regions), so updating state here is thread-safe.
            # Single chokepoint: stamps parent_id (catching any event a hook
            # swapped in downstream of _tree_stamping) and advances HEAD.
            self._state.append_event(e)
            # Track user MessageEvent IDs here so hook callbacks (which may
            # synthesize or alter user messages) are captured in one place.
            if isinstance(e, MessageEvent) and e.source == "user":
                # Track the latest real user message ID for hook-blocked checks.
                # Stop-hook feedback is emitted with source="environment".
                self._state.last_user_message_id = e.id

        callback_list = list(callbacks) if callbacks else []
        # _default_callback (persist) runs before the caller-supplied callbacks
        # (e.g. a PubSub publish), so no subscriber is told about an event that
        # is not on disk yet. compose_callbacks' plain for-loop has no
        # try/except, so if persist raises here, the callbacks after it in the
        # list never run. The visualizer is prepended below and so still renders
        # ahead of persist — that is local terminal output, not an announcement
        # a client can act on.
        composed_list = [_default_callback] + callback_list
```

预测：回调崩溃后事件应该消失吗？

参考：按持久化优先主线，保存成功的事件仍在账本；回调错误属于观测失败。核对存储后再考虑重放，不能倒推任务未发生。

### 活动叶节点决定当前历史

状态添加事件时为其选择父节点，默认以活动叶节点为父，再更新当前 HEAD。事件集合可以形成树，模型通常读取活动分支的历史视图。

把磁盘上所有事件按时间拼接会混入旁支。调试分叉时先标出父关系和 HEAD，再求根到叶路径；时间排序不等于因果顺序。

源码观察：白话翻译
        事件不是简单 append 到数组尾部：未指定 parent 时会指向当前活动 leaf。追加后，普通事件成为新 HEAD。于是一个日志能保存多个分支，而 active branch 只选当前推理需要的路径。

`openhands-sdk/openhands/sdk/conversation/state.py:304-337`

```
    def _stamp_parent_id(self, event: Event) -> Event:
        """Return ``event`` with ``parent_id`` set to the active leaf if unset."""
        if event.parent_id is not None:
            return event
        parent = self._resolve_active_leaf()
        # Empty HEAD over a non-empty log = deliberate new root (navigate_to(None));
        # mark it so it is not misread as a legacy event chained to its neighbour.
        if parent is None and len(self._events) > 0:
            parent = ROOT_PARENT_ID
        return event.model_copy(update={"parent_id": parent})

    def append_event(self, event: Event) -> int:
        """Single storage chokepoint: stamp parent_id, append, advance HEAD.

        Stamping here (not only at the emit callback) ensures no event enters the
        log unstamped, even one a hook swaps in downstream. ``fork`` copies
        pre-stamped events and sets HEAD itself, so it bypasses this.

        Returns:
            The sequence number ``EventLog`` assigned to the appended event.
        """
        event = self._stamp_parent_id(event)
        seq = self._events.append(event)
        # ConversationStateUpdateEvent is a state-sync artifact, not a tree node;
        # advancing HEAD for it would recurse (moving HEAD re-emits one).
        from openhands.sdk.event.conversation_state import (
            ConversationStateUpdateEvent,
        )

        if not isinstance(event, ConversationStateUpdateEvent):
            self.leaf_event_id = event.id
            if self.head_is_empty:  # HEAD now points at a real event again
                self.head_is_empty = False
        return seq
```

预测：恢复时读取整个目录按时间拼接有什么风险？

参考：可能混入其他分支、重复旧事件或丢因果关系。应依据事件父链与活动HEAD重建当前分支。

### 文件写入与索引一致性

EventStore 在锁内同步状态并检查重复 ID、父节点存在等约束，写入事件 JSON 后维护索引。事件引用不能随意指向不存在的父。

文件存在和内存索引更新都有失败边界。独立重建应显式注入存储失败，验证失败前不向订阅者发布；真实跨进程并发与断电一致性留待存储专项。

源码观察：白话翻译
        锁内先同步长度，再拒绝重复 ID 和不存在的显式 parent。JSON 文件成功写入后，内存索引、缓存和长度才一并前进。这里保证的是日志结构，不是工具副作用的事务回滚。

`openhands-sdk/openhands/sdk/conversation/event_store.py:188-238`

```
    def append(self, event: Event) -> int:
        """Append an event with locking for thread/process safety.

        Returns:
            The sequence number (index) the log assigned to ``event``.

        Raises:
            TimeoutError: If the lock cannot be acquired within LOCK_TIMEOUT_SECONDS.
            ValueError: If an event with the same ID already exists or its explicit
                parent does not exist.
        """
        evt_id = event.id

        try:
            with self._fs.lock(self._lock_path, timeout=LOCK_TIMEOUT_SECONDS):
                # Sync with disk only if the marker cannot rule out another writer
                if not self._marker_matches_length():
                    disk_length = self._count_events_on_disk()
                    if disk_length > self._length:
                        self._sync_from_disk(disk_length)

                if evt_id in self._id_to_idx:
                    existing_idx = self._id_to_idx[evt_id]
                    raise ValueError(
                        f"Event with ID '{evt_id}' already exists at index "
                        f"{existing_idx}"
                    )

                if (
                    event.parent_id not in (None, ROOT_PARENT_ID)
                    and event.parent_id not in self._id_to_idx
                ):
                    raise ValueError(
                        f"Parent event '{event.parent_id}' does not exist "
                        f"for event '{evt_id}'"
                    )

                payload = event.model_dump_json(exclude_none=True)
                write_guard = (
                    nullcontext() if self._write_guard is None else self._write_guard()
                )
                idx = self._length
                with write_guard:
                    target_path = self._path(idx, event_id=evt_id)
                    self._fs.write(target_path, payload)
                self._idx_to_id[idx] = evt_id
                self._id_to_idx[evt_id] = idx
                self._event_cache[idx] = event
                self._length += 1
                self._advance_length_marker(idx)
                return idx
```

预测：重复 event ID 应追加第二份吗？

参考：应按存储契约拒绝或显式定义幂等，不能悄悄覆盖。核对父节点、唯一ID与写入顺序，并保留错误。

### 待执行动作优先于新模型调用

Agent.step 可先处理已确认的 pending action；只有需要新决策时才构造上下文并调用模型。一次 step 因而不必等于一次推理请求。

上下文压缩也可能返回 CondensationEvent 而非业务动作。监控应分别计数步、模型请求、动作执行与压缩，避免把循环迭代数当 token 成本。

源码观察：白话翻译
        如果上轮 Action 等待确认，这一轮先执行它，而不是再次问模型。否则 Agent 检查消息闸门、建立会话调用上下文，再把 state.view 转成 LLM 消息。需要压缩时，本轮只发 condensation event。

`openhands-sdk/openhands/sdk/agent/agent.py:651-695`

```
        state = conversation.state
        # Check for pending actions (implicit confirmation)
        # and execute them before sampling new actions.
        pending_actions = ConversationState.get_unmatched_actions(state.active_branch())
        if pending_actions:
            logger.info(
                "Confirmation mode: Executing %d pending action(s)",
                len(pending_actions),
            )
            self._execute_actions(conversation, pending_actions, on_event)
            return

        # Check if the last user message was blocked by a UserPromptSubmit hook
        # If so, skip processing and mark conversation as finished
        if state.last_user_message_id is not None:
            reason = state.pop_blocked_message(state.last_user_message_id)
            if reason is not None:
                logger.info(f"User message blocked by hook: {reason}")
                state.execution_status = ConversationExecutionStatus.FINISHED
                return
        elif state.blocked_messages:
            logger.debug(
                "Blocked messages exist but last_user_message_id is None; "
                "skipping hook check for legacy conversation state."
            )

        # Build per-conversation context once and thread it through all
        # LLM calls in this step (avoids shared mutable state on the LLM).
        call_context: LLMCallContext = conversation.get_llm_call_context()

        # Establish route-aware runtime metadata (cached, no I/O on a hit)
        # before the condenser decides a token threshold, so a routed model's
        # real endpoint limit drives condensation on the first step.
        self.llm.resolve_runtime_metadata()

        # Prepare LLM messages from the cached, incrementally-maintained view.
        # See https://github.com/OpenHands/software-agent-sdk/issues/3053.
        _messages_or_condensation = prepare_llm_messages(
            state.view, condenser=self.condenser, llm=self.llm
        )

        # Process condensation event before agent sampels another action
        if isinstance(_messages_or_condensation, Condensation):
            on_event(_messages_or_condensation)
            return
```

预测：run loop进行了10步，就是10次模型请求吗？

参考：不是。待执行动作、压缩与其他分支可占步骤；根据真实调用事件与费用统计模型请求。

### 模型结果先分派再执行

response_dispatch 优先处理 tool calls，再考虑普通文本或空回复错误。合法工具请求转成 ActionEvent，并在确认策略之后进入执行。

同一回复既有正文又有动作时，先追工具请求的处理路径，不能提前把正文当作最终答案。再分别定位响应解析、确认和工具执行的失败，避免统一归为模型错误。

源码观察：白话翻译
        四类互斥，且有优先级：同时带文字和 tool calls 时仍走工具分支。dispatch 是 SDK 的确定性控制逻辑。

`openhands-sdk/openhands/sdk/agent/response_dispatch.py:45-78`

```
class LLMResponseType(StrEnum):
    """Mutually exclusive classification of an LLM response."""

    TOOL_CALLS = "tool_calls"
    CONTENT = "content"
    REASONING_ONLY = "reasoning_only"
    EMPTY = "empty"


def classify_response(message: Message) -> LLMResponseType:
    """Classify an LLM response message into exactly one type.

    Decision priority (first match wins):
      1. TOOL_CALLS  — message contains tool calls
      2. CONTENT     — message contains non-blank TextContent
      3. REASONING_ONLY — message has reasoning but no visible content
      4. EMPTY       — nothing useful

    This function is pure: no side effects, no logging, no mutation.
    """
    if message.tool_calls:
        return LLMResponseType.TOOL_CALLS

    if any(isinstance(c, TextContent) and c.text.strip() for c in message.content):
        return LLMResponseType.CONTENT

    if (
        message.responses_reasoning_item is not None
        or message.reasoning_content is not None
        or message.thinking_blocks
    ):
        return LLMResponseType.REASONING_ONLY

    return LLMResponseType.EMPTY
```

预测：模型同时给正文与tool_calls，是否立即FINISHED？

参考：按分派主线先处理工具请求；检查Action及确认/执行路径。正文存在不能覆盖待行动。

### FINISHED 是一轮状态

普通文本响应可产生 MessageEvent 并把 Agent 状态置为 FINISHED，等待下一条输入。这个状态表示当前运行阶段结束，不是答案正确的评分。

用户新消息、stop hook 与并发队列可影响后续运行。任务验收应另外测试产物、补丁或回答质量；把状态枚举与评测结果绑定会掩盖失败。

源码观察：白话翻译
        可见文本被记成 agent MessageEvent，然后状态变为 FINISHED：它表示当前 run 等待用户下一次输入，不证明回答内容正确。

`openhands-sdk/openhands/sdk/agent/response_dispatch.py:248-261`

```
    def _handle_content_response(
        self,
        message: Message,
        llm_response: LLMResponse,
        conversation: LocalConversation,
        state: ConversationState,
        on_event: ConversationCallbackType,
        stream: StreamContext | None = None,
    ) -> None:
        """Handle LLM response with text content — finishes conversation."""
        self._emit_message_event(message, llm_response, conversation, on_event, stream)
        self._maybe_emit_vllm_tokens(llm_response, on_event)
        logger.debug("LLM produced a message response - awaits user input")
        state.execution_status = ConversationExecutionStatus.FINISHED
```

预测：FINISHED能作为代码修复测试通过的依据吗？

参考：不能。它说明运行状态；修复结果需要独立测试与产物验证，且要记录错误、动作和观察证据。

### 工具注册表解决能力定位

注册表按名称找到工具定义/工厂，并结合 ConversationState 与 Workspace 实例化执行能力。名称存在只说明可以定位，未证明已调用。

工具描述、参数 schema、执行器和观察编码各有边界。迁移到自建 Runtime 时先保留 ActionID/tool_call_id 关联，再处理应用权限与数据脱敏。

源码观察：白话翻译
        Agent 中的 Tool(name=...) 先按名字查 registry；未动态注册时再查内建类。resolver 拿到当前 ConversationState，因此同一工具名可以按本会话的 Workspace 与参数实例化。

`openhands-sdk/openhands/sdk/tool/registry.py:149-172`

```
def resolve_tool(
    tool_spec: Tool, conv_state: "ConversationState"
) -> Sequence[ToolDefinition]:
    with _LOCK:
        resolver = _REG.get(tool_spec.name)

    if resolver is None:
        from openhands.sdk.tool.builtins import BUILT_IN_TOOL_CLASSES

        tool_class = BUILT_IN_TOOL_CLASSES.get(tool_spec.name)
        if tool_class is None:
            raise KeyError(f"ToolDefinition '{tool_spec.name}' is not registered")
        resolver = _resolver_from_subclass(tool_spec.name, tool_class)

    params = dict(tool_spec.params)
    response_schema = params.pop("response_schema", None)
    tools = resolver(params, conv_state)
    if response_schema is not None:
        if len(tools) != 1:
            raise ValueError(
                "response_schema requires a spec that resolves to exactly one tool"
            )
        tools = [tools[0].set_response_schema(response_schema)]
    return tools
```

预测：注册 terminal 后怎样证明执行发生？

参考：找Action事件、执行入口及匹配的Observation；仅有注册名称或模型schema不足以确认调用。

### Workspace 统一接口不保证隔离

LocalWorkspace 直接使用主机资源。Workspace 抽象提供文件与命令入口，但隔离强度由具体实现和部署决定。

writable/destructive 等标记描述工具属性。它们是否触发授权拒绝，仍需检查策略；同一个 Workspace 接口也不能证明主机、容器和远程环境具有相同权限。

源码观察：白话翻译
        LocalWorkspace 明示直接访问宿主文件系统与命令环境。它适合开发和测试，但不能被描述成容器级或远程级隔离。

`openhands-sdk/openhands/sdk/workspace/local.py:17-34`

```
class LocalWorkspace(BaseWorkspace):
    """Local workspace implementation that operates on the host filesystem.

    LocalWorkspace provides direct access to the local filesystem and command execution
    environment. It's suitable for development and testing scenarios where the agent
    should operate directly on the host system.

    Example:
        >>> workspace = LocalWorkspace(working_dir="/path/to/project")
        >>> with workspace:
        ...     result = workspace.execute_command("ls -la")
        ...     content = workspace.read_file("README.md")
    """

    def __init__(self, *, working_dir: str | Path, **kwargs: Any):
        # Accept Path in signature for ergonomics and type checkers,
        # but normalize to str for the underlying model field.
        super().__init__(working_dir=str(working_dir), **kwargs)
```

预测：有Workspace就能称为安全沙箱吗？

参考：不能。查具体实现与部署边界；Local直接访问主机。描述性工具属性与实际权限/隔离机制分别验证。

### Observation 必须配对动作

工具调用返回 Observation 时保留 ActionID 与 tool_call_id；输入错误可变成 AgentError 等事件。多个同名调用不能按正文或完成顺序配对。

一次工具失败仍须关闭对应请求的消息往返，否则下次模型输入不完整。独立教学对照将展示错配 ID 如何让看起来合理的输出属于错误动作。

源码观察：白话翻译
        Agent 按 tool_name 找到定义并调用它。成功结果被包装成与 Action ID、tool call ID 关联的 ObservationEvent；参数类 ValueError 则变成 AgentErrorEvent，让下一步有机会纠正。

`openhands-sdk/openhands/sdk/agent/agent.py:1384-1446`

```
    def _execute_action_event(
        self,
        conversation: LocalConversation,
        action_event: ActionEvent,
    ) -> list[Event]:
        """Execute a single tool and return the resulting events.

        Called from parallel threads by _execute_actions. This method must
        not mutate shared conversation state (blocked_actions,
        execution_status) — those transitions are handled by the caller
        on the main thread.

        Note: the tool itself receives ``conversation`` and may mutate it
        (e.g. filesystem, working directory). Thread safety of individual
        tools is the tool's responsibility.

        Returns a list of events (observation or error). Events are NOT
        emitted here — the caller is responsible for emitting them in order.
        """
        tool = self.tools_map.get(action_event.tool_name, None)
        if tool is None:
            raise RuntimeError(
                f"Tool '{action_event.tool_name}' not found. This should not happen "
                "as it was checked earlier."
            )

        # Execute actions!
        try:
            if should_enable_observability():
                tool_name = extract_action_name(action_event)
                observation: Observation = observe(
                    name=tool_name,
                    span_type="TOOL",
                    # Only the action is input; the conversation would serialize
                    # as a bare object repr carrying a memory address.
                    ignore_inputs=["conversation"],
                    metadata={"tool_call_id": action_event.tool_call.id},
                )(tool)(action_event.action, conversation)
            else:
                observation = tool(action_event.action, conversation)
            assert isinstance(observation, Observation), (
                f"Tool '{tool.name}' executor must return an Observation"
            )
        except ValueError as e:
            # Tool execution raised a ValueError (e.g., invalid argument combination)
            # Convert to AgentErrorEvent so the agent can correct itself
            err = f"Error executing tool '{tool.name}': {e}"
            logger.warning(err)
            error_event = AgentErrorEvent(
                error=err,
                tool_name=tool.name,
                tool_call_id=action_event.tool_call.id,
                classification=AGENT_OUTCOME,
            )
            return [error_event]

        obs_event = ObservationEvent(
            observation=observation,
            action_id=action_event.id,
            tool_name=tool.name,
            tool_call_id=action_event.tool_call.id,
        )
        return [obs_event]
```

预测：两个terminal动作都输出ok，可以互换结果吗？

参考：不能。依ActionID和tool_call_id配对，保留错误语义；相同正文不能证明同一行动。

### 运行状态不是布尔busy

状态枚举区分 IDLE、RUNNING、等待确认、暂停、完成、错误等阶段。IDLE 意味着可开始，并不是任务已经成功完成。

控制面应明确每个操作允许的源状态、目标状态与事件，避免一个布尔值将暂停和完成混在一起。阅读测试时关注非法转换与并发输入。

源码观察：白话翻译
        IDLE 是“可接新任务”而不是 run 的终点；WAITING_FOR_CONFIRMATION 也不是失败。远程客户端若把初始 IDLE 当终止，会在连接刚建立时误判运行已经结束。

`openhands-sdk/openhands/sdk/conversation/state.py:48-79`

```
class ConversationExecutionStatus(str, Enum):
    """Enum representing the current execution state of the conversation."""

    IDLE = "idle"  # Conversation is ready to receive tasks
    RUNNING = "running"  # Conversation is actively processing
    PAUSED = "paused"  # Conversation execution is paused by user
    WAITING_FOR_CONFIRMATION = (
        "waiting_for_confirmation"  # Conversation is waiting for user confirmation
    )
    FINISHED = "finished"  # Conversation has completed the current task
    ERROR = "error"  # Conversation encountered an error (optional for future use)
    STUCK = "stuck"  # Conversation is stuck in a loop or unable to proceed
    DELETING = "deleting"  # Conversation is in the process of being deleted

    def is_terminal(self) -> bool:
        """Check if this status represents a terminal state.

        Terminal states indicate the run has completed and the agent is no longer
        actively processing. These are: FINISHED, ERROR, STUCK.

        Note: IDLE is NOT a terminal state - it's the initial state of a conversation
        before any run has started. Including IDLE would cause false positives when
        the WebSocket delivers the initial state update during connection.

        Returns:
            True if this is a terminal status, False otherwise.
        """
        return self in (
            ConversationExecutionStatus.FINISHED,
            ConversationExecutionStatus.ERROR,
            ConversationExecutionStatus.STUCK,
        )
```

预测：IDLE可以向用户显示任务完成吗？

参考：应依据业务运行记录判断；IDLE本身只说明状态可等待/开始，和FINISHED、PAUSED、ERROR不同。

### 循环要处理新输入与停止条件

run loop 每轮执行 step，再检查确认、限制和其他停止条件。源码处理新消息与结束状态的竞态，不能简单见 FINISHED 就无条件跳出。

复现“发送后没处理”时需记录消息入账时间、状态转换和循环检查点。静态路径支持提出假设，不代替实际并发压力测试。

源码观察：白话翻译
        每轮恰好调用一次 Agent step。若产生待确认 Action 就停；若超预算或超迭代上限则写结构化错误。源码刻意不在 step 后立刻因 FINISHED 退出，以便锁后到达的新消息仍能被下一轮吸收。

`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:1977-2042`

```
                    # clear the flag before calling agent.step() (user approved)
                    if (
                        self._state.execution_status
                        == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
                    ):
                        self._state.execution_status = (
                            ConversationExecutionStatus.RUNNING
                        )

                    # Mark the step as holding the state lock so state-mutating
                    # tools (e.g. switch_llm) running on worker threads skip
                    # re-acquiring it instead of deadlocking (#3485).
                    self._step_holds_state_lock = True
                    try:
                        self.agent.step(
                            self, on_event=self._on_event, on_token=self._on_token
                        )
                    finally:
                        self._step_holds_state_lock = False
                    iteration += 1

                    # Check for non-finished terminal conditions
                    # Note: We intentionally do NOT check for FINISHED status here.
                    # This allows concurrent user messages to be processed:
                    # 1. Agent finishes and sets status to FINISHED
                    # 2. User sends message concurrently via send_message()
                    # 3. send_message() waits for FIFO lock, then sets status to IDLE
                    # 4. Run loop continues to next iteration and processes the message
                    # 5. Without this design, concurrent messages would be lost
                    if (
                        self.state.execution_status
                        == ConversationExecutionStatus.WAITING_FOR_CONFIRMATION
                    ):
                        break

                    budget_detail = self._budget_exceeded_detail()
                    if budget_detail and (
                        self._state.execution_status
                        != ConversationExecutionStatus.FINISHED
                    ):
                        self._emit_run_limit_error("MaxBudgetReached", budget_detail)
                        break

                    if iteration >= self.max_iteration_per_run:
                        # If the agent finished on this final iteration,
                        # preserve the FINISHED status rather than
                        # overwriting it with ERROR.
                        if (
                            self._state.execution_status
                            == ConversationExecutionStatus.FINISHED
                        ):
                            break
                        error_msg = (
                            f"Agent reached maximum iterations limit "
                            f"({self.max_iteration_per_run})."
                        )
                        logger.error(error_msg)
                        self._state.execution_status = ConversationExecutionStatus.ERROR
                        self._on_event(
                            ConversationErrorEvent(
                                source="environment",
                                code="MaxIterationsReached",
                                detail=error_msg,
                            )
                        )
                        break
```

预测：为何不能把循环改成step后遇FINISHED立刻break？

参考：可能忽略该期间新入账消息或停止hook的继续条件；先冻结竞态语义与队列检查，再用受控输入验证。

### 中断需要补全未完成工具往返

中断路径可为已有 Action 但缺 Observation 的调用生成合成错误观察，避免恢复后模型看到悬空工具请求。

中断不等于现实副作用回滚；工具可能已完成写入却还未返回观察。恢复应保留“结果未知”的边界并查询/幂等处理，不能用合成错误断言实际没有执行。

源码观察：白话翻译
        interrupt 不是删除会话。SDK 还为没有 Observation 的在途 Action 补合成错误结果，避免恢复后给模型一段结构不完整的 tool history。

`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:2507-2542`

```
        except asyncio.CancelledError:
            # CancelledError is intentionally NOT re-raised.  ``interrupt()``
            # uses ``asyncio.Task.cancel()`` to break out of ``arun()`` and
            # expects the task to terminate cleanly.  Re-raising would
            # propagate the cancellation to EventService/caller which would
            # surface it as an unexpected error.  Instead we transition to
            # PAUSED so the conversation can be resumed later.
            logger.info("arun() interrupted via task cancellation")
            with self._state:
                updated_agent_state = dict(self._state.agent_state)
                inflight_prompt_user_message_id = updated_agent_state.pop(
                    ACP_INFLIGHT_PROMPT_USER_MESSAGE_ID, None
                )
                superseded_by_new_message = bool(
                    updated_agent_state.pop(ACP_SUPERSEDE_INFLIGHT_PROMPT, False)
                )
                completed_cancelled_prompt = (
                    self._state.execution_status == ConversationExecutionStatus.FINISHED
                )
                if (
                    superseded_by_new_message or completed_cancelled_prompt
                ) and inflight_prompt_user_message_id is not None:
                    updated_agent_state[ACP_LAST_PROMPT_USER_MESSAGE_ID] = (
                        inflight_prompt_user_message_id
                    )
                self._state.agent_state = updated_agent_state

                # Emit synthetic error observations for any ActionEvents
                # that were in-flight when the interrupt landed.  Without
                # these the LLM history would contain tool-call requests
                # with no tool-result, which causes provider errors on
                # the next completion call.
                self._emit_orphaned_action_errors()

                self._state.execution_status = ConversationExecutionStatus.PAUSED
                self._on_event(InterruptEvent())
```

预测：收到中断错误观察，能保证工具没有改文件吗？

参考：不能。合成观察修复协议完整性，不撤销外部动作。检查执行账本、文件证据与请求幂等，明确未知结果。

### 远程发送与调度仍是两件事

Server 的消息入口可通过 request.run 选择是否调度运行；run 入口还处理重复请求与生命周期约束。HTTP 接受请求不等于 Agent 已经完成。

客户端应展示接受、排队、运行、完成与失败，不能把 200 响应当模型结果。服务器 fallback 到线程运行的路径也不是异步性能保证。

源码观察：白话翻译
        事件端点把请求体重建为 SDK Message，再交给当前 conversation 的 EventService；request.run 决定只入队还是连带请求运行。

`openhands-agent-server/openhands/agent_server/event_router.py:213-221`

```
@event_write_router.post("")
async def send_message(
    request: SendMessageRequest,
    event_service: EventService = Depends(get_event_service),
) -> Success:
    """Send a message to a conversation"""
    message = Message(role=request.role, content=request.content)
    await event_service.send_message(message, request.run)
    return Success()
```

预测：远程接口200返回后能立即读最终答案吗？

参考：先确定request.run和调度状态，再追踪事件或完成状态；200说明入口接受，不保证Agent完成。

### 订阅重放与实时流分开

WebSocket 把连接绑定 Conversation，组织历史订阅与实时事件。鉴权入口、历史重放和网络交付是不同责任。

断线后可能重放，客户端需依据 event ID 处理重复与缺口。静态代码不证明网络 exactly once；本课没有启动生产服务器或测鉴权。

源码观察：白话翻译
        subscriber 先通过认证并绑定 conversation。客户端可只听新事件，也可要求补发全部或某个时间点后的历史，再继续实时订阅。

`openhands-agent-server/openhands/agent_server/sockets.py:227-301`

```
@conversation_sockets_router.websocket("/events/{conversation_id}")
async def events_socket(
    conversation_id: UUID,
    websocket: WebSocket,
    session_api_key: Annotated[str | None, Query(alias="session_api_key")] = None,
    resend_mode: Annotated[
        Literal["all", "since"] | None,
        Query(
            description=(
                "Mode for resending historical events on connect. "
                "'all' sends all events, 'since' sends events after 'after_timestamp'."
            )
        ),
    ] = None,
    after_timestamp: Annotated[
        datetime | None,
        Query(
            description=(
                "Required when resend_mode='since'. Events with timestamp >= this "
                "value will be sent. Accepts ISO 8601 format. Timezone-aware "
                "datetimes are converted to server local time; naive datetimes "
                "assumed in server timezone."
            )
        ),
    ] = None,
    # Deprecated parameter - kept for backward compatibility
    resend_all: Annotated[
        bool,
        Query(
            include_in_schema=False,
            deprecated=True,
        ),
    ] = False,
):
    """WebSocket endpoint for conversation events.

    Args:
        conversation_id: The conversation ID to subscribe to.
        websocket: The WebSocket connection.
        session_api_key: Optional API key for authentication.
        resend_mode: Mode for resending historical events on connect.
            - 'all': Resend all existing events
            - 'since': Resend events after 'after_timestamp' (requires after_timestamp)
            - None: Don't resend, just subscribe to new events
        after_timestamp: Required when resend_mode='since'. Events with
            timestamp >= this value will be sent. Timestamps are interpreted in
            server local time. Timezone-aware datetimes are converted to server
            timezone. Enables efficient bi-directional loading where REST fetches
            historical events and WebSocket handles events after a specific point.
        resend_all: DEPRECATED. Use resend_mode='all' instead. Kept for
            backward compatibility - if True and resend_mode is None, behaves
            as resend_mode='all'.
    """
    if not await _accept_authenticated_websocket(websocket, session_api_key):
        return

    logger.info(f"Event Websocket Connected: {conversation_id}")
    conv_service = _get_conversation_service(websocket)
    try:
        event_service = await conv_service.get_event_service(conversation_id)
    except CredentialBindingActivationRequired:
        await websocket.close(
            code=1013,
            reason="credential_binding_activation_required",
        )
        return
    if event_service is None:
        logger.warning(f"Converation not found: {conversation_id}")
        await websocket.close(code=4004, reason="Conversation not found")
        return

    try:
        subscriber_id = await event_service.subscribe_to_events(
            _WebSocketSubscriber(websocket)
        )
```

预测：重连后同一事件再次出现应怎样处理？

参考：按稳定event ID和游标去重并检查缺口，必要时对照持久历史；不要假设每条只传一次。

### fork 复制历史不回滚工作区

fork 从历史切点组织新 Conversation 与 Agent 记忆，但外部 Workspace 的文件和操作不是随事件树自动倒带。

需要可重复的分叉实验时，先说明目录是否复制、文件是否快照，或是否使用独立工作区。事件账本恢复的是推理视图；行动涉及的外部状态要另外核对。

源码观察：白话翻译
        fork 像用同一剧本成立复排剧组。它复制 Agent 记忆，可从某个事件切点继续，但源会话仍在。

`openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py:787-818`

```
    def fork(
        self,
        *,
        conversation_id: ConversationID | None = None,
        agent: AgentBase | None = None,
        title: str | None = None,
        tags: dict[str, str] | None = None,
        reset_metrics: bool = True,
        from_event_id: EventID | None = None,
    ) -> "LocalConversation":
        """Deep-copy this conversation with a new ID.

        Events are copied so the source remains immutable. The fork starts
        in ``execution_status='idle'``; calling ``run()`` resumes from the
        copied state — meaning the agent has full event memory of the source.

        Args:
            conversation_id: ID for the forked conversation (auto-generated
                if ``None``).
            agent: Agent for the fork. Defaults to a deep-copy of the
                source agent.
            title: Optional title for the forked conversation.
            tags: Optional tags for the forked conversation.
            reset_metrics: If ``True`` (default), cost/token stats start
                fresh on the fork.
            from_event_id: If set, copy only the branch up to this event
                (``path_to_root``) and set the fork's HEAD there. If ``None``
                (default), copy the whole log and keep the source's HEAD.

        Returns:
            A new ``LocalConversation`` that shares the same event history
            but has its own identity and independent state going forward.
```

预测：从改文件前的事件fork，文件会自动恢复吗？

参考：不会由事件分叉自动保证。另定义Workspace快照/复制与隔离，记录外部状态；区分历史分支与现实副作用。

### 闭卷复述与迁移

事件历史已恢复，但工作区文件不同，为什么不能称为完整恢复？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## DeerFlow · 一次研究请求穿过多个服务

一次研究请求穿过多个服务

来源：https://github.com/StormTian/deer-flow

提交：`5b83cb502c967e2952d32155a21c01ee739f1660`；访问：2026-10-01

证据：独立 Python 教学模型五场景；原全栈 Runtime 未执行。

冻结的是本地 fork 的提交加工作区快照；嵌入摘录是核验依据，远端基础提交不一定包含本地修改。

排除：DeerFlow 全栈未启动，真实模型/工具/MCP/外部 sandbox 未调用。；仓库内 production tests 仅阅读，没有执行通过声明。；Redis/Postgres/SQLite 生产运行、多 worker lease、跨进程恢复/rollback 和真实权限隔离未测。；学习者没有提交答案，本课不会生成 learner-state 或宣称 mastery。

### 本案例阅读任务

追踪研究请求经过前端、Gateway Runtime 和工具账本的过程，定位事件缺口与长任务上下文。

读前准备：第 2、3、6 章；知道 HTTP 请求和 SSE 事件流。SSE cursor 表示读取位置，不等同于 checkpoint。

1. 先画服务拓扑，列出 thread、run、checkpoint 和 cursor 的职责。
2. 追 Run 接纳、工具装配、消息/非消息流和产物登记。
3. 检查回放缺口、委派终态和摘要恢复，核对本地快照及排除范围。

检验理解：给出一个回放缺口和一个迟到委派事件，说明前端或账本应怎样处理。

判断标准：缺口需要重载持久状态后继续观察；同一(run,id)的非终态不得覆盖终态。五个独立模型不代表全栈验证。

阅读主线：从前端消息进入 Gateway Runtime，再看主/子 Agent、工具账本、事件回放与长任务上下文。

### 服务拓扑与 harness

先分清请求经过的服务。Nginx 负责路由，Gateway 提供 HTTP 入口并拥有内嵌 Runtime，harness 则是运行时装配的库。不能仅凭 harness 这个名字把它画成独立服务。

本地快照中的统一入口将 /api/langgraph/* 转到 Gateway，并关闭 SSE 代理缓冲。沿这条路由读下去，才能定位请求接纳和事件发送分别发生在哪里。

源码观察：统一入口将 /api/langgraph/* 改写到 Gateway，并关闭 SSE 代理缓冲。

`docker/nginx/nginx.local.conf:67-82`

```
        location /api/langgraph/ {
            rewrite ^/api/langgraph/(.*) /api/$1 break;
            proxy_pass http://gateway;
            proxy_http_version 1.1;

            # Headers
            proxy_set_header Host $http_host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection '';

            # SSE/Streaming support
            proxy_buffering off;
            proxy_cache off;
            proxy_set_header X-Accel-Buffering no;
```

预测：只启动 frontend 能否执行研究？哪些角色缺席？

参考：不能从 frontend 启动推导完整研究运行。需要 Gateway 的接纳/worker、有效模型及任务所用依赖；proxy 是统一入口而不是执行器。

### Thread、Run、Checkpoint 与事件 ID

thread 标识会话范围，run 标识一次执行，checkpoint 标识可恢复的状态，SSE cursor 标识事件读取位置。它们对应不同生命周期，排错时需要同时保留，不能互相替代。

先看请求中的 checkpoint、stream 与并发策略，再检查断线处理。本快照默认 on_disconnect=cancel；创建者断线与只读观察者断线还要按各自路径分析。

源码观察：请求契约区分 checkpoint、stream 和并发策略；默认 on_disconnect=cancel。

`backend/app/gateway/run_models.py:46-57`

```
    checkpoint_id: str | None = Field(default=None, description="Resume from checkpoint")
    checkpoint: dict[str, Any] | None = Field(default=None, description="Full checkpoint object")
    interrupt_before: list[str] | Literal["*"] | None = Field(default=None, description="Nodes to interrupt before")
    interrupt_after: list[str] | Literal["*"] | None = Field(default=None, description="Nodes to interrupt after")
    stream_mode: list[RunStreamMode] | RunStreamMode | None = Field(default=None, description="Supported stream mode(s)")
    stream_subgraphs: bool = Field(default=False, description="Include subgraph events")
    stream_resumable: Literal[False] | None = Field(default=None, description="Compatibility placeholder; only the SDK's non-resumable default (null/false) is accepted")
    on_disconnect: Literal["cancel", "continue"] = Field(default="cancel", description="Behaviour on SSE disconnect")
    on_completion: None = Field(default=None, description="Compatibility placeholder; completion behavior is not supported")
    multitask_strategy: Literal["reject", "rollback", "interrupt"] = Field(default="reject", description="Concurrency strategy")
    after_seconds: None = Field(default=None, description="Compatibility placeholder; delayed execution is not supported")
    if_not_exists: Literal["create"] = Field(default="create", description="Compatibility default; missing threads are created")
```

预测：同 thread 发两轮，第二轮 Last-Event-ID 能否用第一轮 checkpoint_id 代替？

参考：不能。Run 观察 cursor 属于该 Run 的保留事件序列；checkpoint_id 指图状态历史。两轮可复用 thread，但需要不同 Run 的事件身份。

### 状态字段与 reducer

ThreadState 把消息、目标、委派、Skill、任务笔记和摘要放在不同状态字段中。读更新代码时，先找到字段所属 channel，再检查对应 reducer 如何合并。

状态可能持久化多个 channel；不能只把 messages 当作全部任务状态。预测一次更新时，要分别说明消息和其他字段会被追加、替换还是归并。

源码观察：ThreadState 将消息之外的目标、委派、Skill、任务笔记和摘要分成独立状态字段。

`backend/packages/harness/deerflow/agents/thread_state.py:352-369`

```
class ThreadState(AgentState):
    sandbox: SandboxStateField
    thread_data: NotRequired[ThreadDataState | None]
    title: NotRequired[str | None]
    artifacts: Annotated[list[str], merge_artifacts]
    todos: Annotated[list | None, merge_todos]
    goal: Annotated[GoalState | None, merge_goal]
    uploaded_files: NotRequired[list[dict] | None]
    viewed_images: Annotated[dict[str, ViewedImageData], merge_viewed_images]  # image_path -> metadata (no base64)
    promoted: Annotated[PromotedTools | None, merge_promoted]
    delegations: Annotated[list[DelegationEntry], merge_delegations]
    skill_context: Annotated[list[SkillEntry], merge_skill_context]
    tool_artifacts: Annotated[list[ArtifactEntry], merge_tool_artifacts]
    tool_artifact_processed: Annotated[list[str], merge_artifacts]
    task_notes: Annotated[dict | None, TaskNotesChannel(dict | None, merge_task_notes)]
    task_history: NotRequired[dict | None]
    summary_text: NotRequired[str | None]
    background_tasks: NotRequired[list[BackgroundTaskState]]
```

预测：artifacts 和 summary_text 为什么不直接当作一条消息？

参考：路径清单与摘要有独立职责：artifacts 可以去重合并，summary 为独立 LastValue 数据；它们可投影到 UI/模型，却不必新增持久消息。

### 消息元数据与模式派生

提交消息时，helper 将上传文件和项目暂存文件合并到 human 消息的元数据，同时保留其他 additional_kwargs。追输入时应核对完整消息，避免只检查正文。

前端 mode 还会派生 thinking、plan、subagent 等 context 开关。模式名称只是入口，实际执行行为需要继续追这些具体字段。

源码观察：上传和项目暂存文件在同一 helper 合并，保留其它 additional_kwargs。

`frontend/src/core/threads/hooks.ts:183-195`

```
export function buildHumanMessageAdditionalKwargs(
  additionalKwargs: Record<string, unknown> | undefined,
  files: FileInMessage[],
): Record<string, unknown> {
  const stagedFiles = Array.isArray(additionalKwargs?.files)
    ? (additionalKwargs.files as FileInMessage[])
    : [];
  const allFiles = [...stagedFiles, ...files];
  return {
    ...additionalKwargs,
    ...(allFiles.length > 0 ? { files: allFiles } : {}),
  };
}
```

源码观察：前端模式变为 thinking/plan/subagent 等 context 字段。

`frontend/src/core/threads/hooks.ts:264-275`

```
    thinking_enabled: settings.mode !== "flash",
    is_plan_mode: settings.mode === "pro" || settings.mode === "ultra",
    subagent_enabled: settings.mode === "ultra",
    reasoning_effort:
      settings.reasoning_effort ??
      (settings.mode === "ultra"
        ? "high"
        : settings.mode === "pro"
          ? "medium"
          : settings.mode === "thinking"
            ? "low"
            : undefined),
```

预测：有 staged file A、quote、本次 upload B，Ultra 提交的结果应是什么？

参考：additional_kwargs 保留 quote，files 为 A、B；thinking_enabled=true、is_plan_mode=true、subagent_enabled=true。这是请求 intent，服务端继续准入。

### 增量消息与非消息状态归属

主聊天消费 messages-tuple、updates 和 custom 三类增量流。SDK 负责 live messages 的拼接；DeerFlow 处理 updates 中的非消息状态。

updates 提供给 reducer 的更新，与消息流的拼接职责不同。排查重复或丢失时，先确认字段归谁处理，再检查更新顺序，避免两个消费者同时改写同一份消息。

源码观察：主聊天默认使用 messages-tuple、updates、custom 三类增量流。

`frontend/src/core/api/stream-mode.ts:11-15`

```
export const CHAT_RUN_STREAM_MODES = [
  "messages-tuple",
  "updates",
  "custom",
] as const;
```

源码观察：updates 是 reducer 输入；消息拼接由 SDK 独占。

`frontend/src/core/threads/stream-state.ts:93-106`

```
/**
 * Fold a LangGraph `updates` frame into the state fields rendered by the chat
 * UI. Updates are grouped by node name and carry reducer inputs, not complete
 * state snapshots, so these fields must mirror the reducers in
 * `deerflow.agents.thread_state` rather than being shallowly assigned.
 *
 * `messages` is deliberately excluded. The SDK's `messages-tuple` manager owns
 * chunk assembly and same-id replacement; applying the node's messages update
 * through `mutate` as well would duplicate messages and bypass chunk merging.
 */
export function reduceThreadStateUpdates(
  previous: AgentThreadState,
  data: unknown,
): ThreadStatePatch | undefined {
```

预测：updates.messages 又被 mutate 一次为什么危险？

参考：同一逻辑消息会同时被 messages-tuple SDK 和自写 updates 路径处理，造成重复/错序/跳过 chunk merge。按字段 reducer 折叠非消息状态即可。

### Run 创建与恢复重试

创建 Run 的 POST 会接纳新的执行，因此本快照关闭了这条请求的自动重试。恢复用 GET 读取已存在的 Run，保留单独的 HTTP 重试策略。

排查超时时，先判断失败发生在创建还是观察阶段。不能将 GET 的重试方式直接套到创建 POST 上，否则可能把一次任务变成重复接纳。

源码观察：创建 Run 的 POST 关闭自动重试，恢复 GET 保持单独的 HTTP 重试。

`frontend/src/core/api/api-client.ts:465-481`

```
  // Creating a run is not idempotent. Retrying an ambiguous gateway failure
  // can create the same run more than once after the backend accepted the
  // original request. The SDK also uses this client's transport for recovery
  // GETs, which must retain normal HTTP retries (including transient 5xx).
  const streamRecoveryClient = new StreamRecoveryClient({ apiUrl });
  const runCreationClient = new RunsClient({
    apiUrl,
    callerOptions: {
      maxRetries: 0,
      fetch: (...args: Parameters<typeof fetch>) =>
        args[1]?.method === "GET"
          ? streamRecoveryClient.fetchWithRetries(...args)
          : fetch(...args),
    },
    onRequest: injectCsrfHeader,
  });
  const originalRunStream = runCreationClient.stream.bind(runCreationClient);
```

预测：创建 POST 服务器接受但响应丢失，为什么不能自动重发？

参考：它可能造成第二个 Run。先用已知 run_id/Location 或后端记录核对；已有 Run 的 GET 观察恢复可保留读取重试。显式 idempotency 需另外的稳定键和请求一致性契约。

### 持久接纳与 worker 所有权

RunManager 先持久接纳 Run，再在不 await 其他操作的情况下挂上后台 task；挂载失败有 pending 失败处理。读取这段代码时，同时核对持久记录与当前 worker 是否真正拥有执行 task。

从 store 读取的其他 worker 记录是 detached snapshot。它可用于观察，不能注册成当前 worker 的 Run，否则本地记录与执行所有权会不一致。

源码观察：持久接纳后不 await 就挂上后台 task，挂载失败有 pending 失败处理。

`backend/app/gateway/services.py:2117-2133`

```
                    return record

                worker = run_after_metadata(record)
                try:
                    # No await is allowed between durable admission and task
                    # attachment. Metadata setup runs inside the attached
                    # worker so a pending cancellation can bypass stalled
                    # thread-store IO and still reach run_agent's startup
                    # barrier / stream finalization.
                    record.task = asyncio.create_task(worker)
                except Exception as exc:
                    worker.close()
                    await run_mgr.fail_start_if_pending(
                        record.run_id,
                        error=f"Failed to attach run worker: {exc}",
                    )
                    raise
```

源码观察：从 store 读出的 peer 记录为 detached snapshot，不应注册成本 worker 的 Run。

`backend/packages/harness/deerflow/runtime/runs/manager.py:467-476`

```
    def _record_from_store(row: dict[str, Any]) -> RunRecord:
        """Build a read-only runtime record from a serialized store row.

        The result is a detached ``store_only`` snapshot. Never register it in
        ``_runs``: only the owning worker's task lifecycle updates and removes
        local records, so a registered snapshot would never leave.

        NULL status/on_disconnect columns (e.g. from rows written before those
        columns were added) default to ``pending`` and ``cancel`` respectively.
        """
```

预测：在 durable admission 和 record.task=create_task 之间加 await 会新增什么故障窗口？

参考：取消/阻塞可留下已接纳 pending Run 却没有 attached task。当前代码不在该段 await；task 创建异常显式 fail pending。peer snapshot 也不能当自己的 worker 注册。

### SSE replay gap 与快照重载

事件流有保留窗口。cursor 过旧且能被解析时，服务返回 gap；窗口内匹配的 cursor 则从下一事件开始回放。过期事件不能靠有界流完整补回。

SSE gap 包含保留范围和 reload_durable_state 恢复指令。前端先发恢复控制事件，再读持久 state 并继续 join；状态读取失败会显式形成 gap error。定位缺口时要分别检查回放窗口和状态重载。

源码观察：过旧且可解析的 cursor 返回 gap，窗口内匹配从下一事件回放。

`backend/packages/harness/deerflow/runtime/stream_bridge/memory.py:87-100`

```
        seq = self._parse_event_seq(last_event_id)
        if seq is not None:
            if seq < stream.start_offset:
                return self._make_gap(stream, last_event_id)
            local_index = seq - stream.start_offset
            if 0 <= local_index < len(stream.events) and stream.events[local_index].id == last_event_id:
                return stream.start_offset + local_index + 1

        if stream.events:
            logger.warning(
                "last_event_id=%s not found in retained buffer; replaying from earliest retained event",
                last_event_id,
            )
        return stream.start_offset
```

源码观察：SSE gap 提供 retained bounds 和 reload_durable_state 恢复指令。

`backend/app/gateway/services.py:2363-2376`

```
            if isinstance(entry, StreamGap):
                gap_emitted = True
                yield format_sse(
                    "gap",
                    {
                        "code": "stream_replay_gap",
                        "run_id": record.run_id,
                        "requested_event_id": entry.requested_event_id,
                        "earliest_available_event_id": entry.earliest_available_event_id,
                        "latest_available_event_id": entry.latest_available_event_id,
                        "recovery": "reload_durable_state",
                    },
                )
                return
```

源码观察：前端发出恢复控制事件，再读取持久 state；读取失败显式变成 gap error。

`frontend/src/core/api/api-client.ts:382-399`

```
    // The SDK would otherwise ignore an unknown `gap` event and report a
    // normal finish. Surface a custom control event to DeerFlow's hook, reload
    // durable values, then resume after the retained tail when it exists
    // (or rejoin without a cursor if the buffer is empty).
    clearReconnectRun(threadId, runId);
    yield {
      event: "custom",
      data: { type: "stream_replay_gap", ...gap },
    };

    const durableState = await client.threads
      .getState(threadId, undefined, { signal })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") {
          throw error;
        }
        throw new StreamReplayGapError(gap, recoveryAttempts, error);
      });
```

预测：仅保留 4..6，客户端 cursor=1，正确流程和失败边界是什么？

参考：memory bridge 返回 gap；SSE 携 bounds；前端发 custom 恢复事件、重载 durable state、从 retained tail join 同 Run。读取失败或五次预算耗尽显式 error，不新建 Run。

### 观察断线与 checkpoint 恢复

join 用于只读观察已有执行，创建者的断线策略不会直接施加到 join 观察者。重新连接事件流时，先确认调用者是在观察，还是在创建或恢复执行。

checkpoint 恢复还受 storage mode 和 lineage 约束。full 进程拒绝将 delta 检查点的空或部分状态暴露为完整状态，因此事件重连成功不能证明检查点已经正确恢复。

源码观察：创建者断线策略不施加到只读 join 观察者。

`backend/app/gateway/services.py:2315-2325`

```
    The ``finally`` block implements ``on_disconnect`` semantics, but only for
    the stream returned by the *creating* endpoint (``apply_on_disconnect=True``):

    - ``cancel``: abort the background task on client disconnect.
    - ``continue``: let the task run; events are discarded.

    Join/observer streams pass ``apply_on_disconnect=False``: the creator's
    cancel-on-disconnect policy expresses the creator's intent for their own
    connection, and a read-only observer closing a join must not cancel the
    run (a runs:read-only credential would otherwise cancel without
    runs:cancel just by disconnecting).
```

源码观察：full 进程拒绝暴露 delta 检查点的空/部分状态。

`backend/packages/harness/deerflow/runtime/checkpoint_mode.py:114-129`

```
def raise_if_snapshot_incompatible(snapshot: Any, mode: CheckpointChannelMode) -> None:
    """Fail closed when a full-mode process materialized a delta checkpoint.

    Runs on the ``StateSnapshot`` returned by ``get_state``/``get_state_history``,
    so reads cost a single checkpoint fetch: the marker lives in
    ``snapshot.metadata``. Reading the blob is harmless; silently *using* the
    empty/partial state is the danger, and the caller never receives it.
    """
    if mode == "full" and state_snapshot_uses_delta(snapshot):
        raise CheckpointModeMismatchError("Thread requires delta mode; materialize and convert its checkpoints before using full mode.")


def raise_if_checkpoint_tuple_incompatible(checkpoint_tuple: Any, mode: CheckpointChannelMode) -> None:
    """Fail closed before exposing raw checkpoint metadata across modes."""
    if mode == "full" and checkpoint_tuple_uses_delta(checkpoint_tuple):
        raise CheckpointModeMismatchError("Thread requires delta mode; materialize and convert its checkpoints before using full mode.")
```

预测：full 进程读取 delta thread，或只读 observer 断线，分别应该怎样处理？

参考：前者 fail closed 并要求匹配模式/转换；后者关闭订阅且不套用创建者 cancel-on-disconnect。两者分属状态语义与连接权限。

### 有效配置的键存在性

有效配置按 request > agent > default 选择，判断依据是 key in cfg，也就是键是否存在。显式 false 是已经提供的配置值，不能因为它为假就当成缺失。

核对配置时，分别列出来源和最终值；只看一个开关是否为真，会掩盖请求对 Agent 默认值的覆盖。

源码观察：以键存在性实现 request > agent > default，显式 false 不被默认值覆盖。

`backend/packages/harness/deerflow/agents/lead_agent/agent.py:164-177`

```
def _resolve_runtime_option(cfg: dict, key: str, agent_value, default):
    """Resolve a runtime option with ``request > agent config > default`` precedence.

    ``key in cfg`` (not ``cfg.get(key)``) distinguishes "request omitted the
    field" from "request set it to a falsy value", so a request-supplied
    ``thinking_enabled: false`` is honored instead of falling through to the
    agent default. ``agent_value`` is used only when it is not ``None`` (a
    custom agent's unset field means "do not override" — issue #4336).
    """
    if key in cfg:
        return cfg[key]
    if agent_value is not None:
        return agent_value
    return default
```

预测：agent true、request false，改成 cfg.get(key) or agent_value 会破坏什么？

参考：会将显式关闭重新开启；契约是 request>agent>default。需要分别验证 false、0/空值（按字段有效性）与省略，不能只测 truthy 输入。

### 工具授权与 deferred schema

先按授权规则过滤工具，再装配 deferred schema，决定哪些能力当前可见、哪些可以后续发现。late tools 与 configured tools 各有归属，不能只看最终工具名称列表。

实际 create_agent 接收 model、tools、middleware、prompt 及与 mode 匹配的 state schema。用于描述能力的 descriptor 和真正运行的 graph 应使用同一次装配结果，避免描述与执行不同。

源码观察：授权过滤先于 deferred schema 装配，late tools 与 configured tools 有各自归属。

`backend/packages/harness/deerflow/agents/lead_agent/agent.py:1311-1319`

```
    authorized_tools, _authz_provider = apply_tool_authorization(
        authorization_candidates,
        context=cfg,
        app_config=resolved_app_config,
    )
    configured_tools = [tool for tool in authorized_tools if id(tool) in configured_tool_ids]
    late_tools = [tool for tool in authorized_tools if id(tool) not in configured_tool_ids]
    final_tools, setup = assemble_deferred_tools(configured_tools, enabled=resolved_app_config.tool_search.enabled)
    final_tools.extend(late_tools)
```

源码观察：真实 create_agent 传入 model、tools、middleware、prompt 与 mode 匹配的 state schema。

`backend/packages/harness/deerflow/agents/lead_agent/agent.py:1357-1364`

```
    graph = create_agent(
        model=chat_model,
        tools=final_tools,
        middleware=normalize_middleware_state_schemas(middlewares, mode),
        system_prompt=system_prompt,
        state_schema=get_thread_state_schema(mode),
        context_schema=dict,
    )
```

预测：tool_search promotion 是否可使被授权层拒绝的工具重新可执行？

参考：不应。candidate 先经过授权，再做 deferred schema；active Skill 还有调用 gate。promotion 控制模型可见性，不授予 user 权限。

### Middleware 顺序与控制权

DurableContext 放在摘要之前，先捕获需要独立保存的上下文状态。若只按 middleware 名称列清单，会漏掉先后顺序带来的输入差异。

安全终止 guard 的 after_model 顺序有明确约束，Clarification 位于内置尾部。读 dispatch 与 wrapper 时分别追控制权，不能把一种回调顺序推广到全部包装流程。

源码观察：DurableContext 位于摘要之前，捕获独立的上下文状态。

`backend/packages/harness/deerflow/agents/lead_agent/agent.py:618-628`

```
    # Capture completed task delegations and loaded skill files before
    # summarization can compact them, then inject durable context channels
    # (summary + ledger + skills) into model calls.
    from deerflow.agents.middlewares.durable_context_middleware import DurableContextMiddleware

    middlewares.append(
        DurableContextMiddleware(
            skills_container_path=resolved_app_config.skills.container_path,
            skill_file_read_tool_names=resolved_app_config.summarization.skill_file_read_tool_names,
            inject_tool_artifacts=resolved_app_config.tool_artifacts.enabled and resolved_app_config.tool_artifacts.inject_model_context,
            task_continuity_enabled=getattr(getattr(resolved_app_config, "task_continuity", None), "enabled", False) is True,
```

源码观察：安全终止 guard 的 after_model 顺序有明确约束；Clarification 位于内置尾部。

`backend/packages/harness/deerflow/agents/lead_agent/agent.py:766-776`

```
    # SafetyFinishReasonMiddleware — suppress tool execution when the provider
    # safety-terminated the response. Registered after the terminal-response
    # and custom/configured middlewares so LangChain's reverse-order after_model
    # dispatch runs Safety first; cleared tool_calls then flow through the
    # remaining accounting/terminal guards without firing extra alarms.
    safety_config = resolved_app_config.safety_finish_reason
    if safety_config.enabled:
        middlewares.append(SafetyFinishReasonMiddleware.from_config(safety_config))

    # ClarificationMiddleware should always be last
    middlewares.append(ClarificationMiddleware())
```

预测：把 DurableContext 放到 summarization 后，或让 clarification 的兄弟工具继续，分别破坏什么？

参考：前者可能丢失已压缩的委派/Skill 信息；后者在用户回应前执行未决副作用。不能把列表顺序当所有 hooks 正向执行，也需考虑 extension composition。

### 激活 Skill 的运行工具政策

enabled Skill 提供可发现的元数据；激活或受支持的读取才形成 allowed-tools 政策。持久化引用在重新使用时还要重新授权，因此发现某个 Skill 不等于其政策已生效。

检查分别发生在模型与工具边界。工具调用阶段再次应用 active policy，既能阻止执行，也会过滤 tool_search 的 promotion。应沿激活、发现和执行三条路径核对。

源码观察：enabled Skill 是可发现元数据，allowed-tools 在激活/读取后才应用；持久引用重新授权。

`backend/packages/harness/deerflow/agents/lead_agent/agent.py:601-615`

```
    # Enabled skills are only discoverable metadata. Apply allowed-tools at
    # runtime after explicit slash activation or an actual skill-file load.
    from deerflow.agents.middlewares.skill_tool_policy_middleware import SkillToolPolicyMiddleware

    middlewares.append(
        SkillToolPolicyMiddleware(
            available_skills=available_skills,
            app_config=resolved_app_config,
            user_id=user_id,
            slash_source_owner_token=slash_source_owner_token,
            # Persisted skill_context entries are re-authorized against the
            # skill:activate decision before their allowed-tools apply (the
            # policy may have changed since the entry was stamped).
            skill_authorization=skill_authorization,
        )
```

源码观察：工具调用阶段再执行 active policy，阻止执行并过滤 tool_search 的 promotion。

`backend/packages/harness/deerflow/agents/middlewares/skill_tool_policy_middleware.py:470-483`

```
    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        policy = self._active_policy(request)
        if not policy[1]:
            return handler(request)
        allowed = self._allowed_names(request, policy=policy)
        blocked = self._blocked_tool_message(request, allowed=allowed)
        if blocked is not None:
            return blocked
        return self._filter_tool_search_result(request, handler(request), allowed=allowed)
```

预测：仅将 Skill enabled=true 是否自动限制全部 tools？task 是否天然豁免？

参考：前者不会，只有 active sources 形成约束；task 是业务工具也需显式 permission，不能因委派是框架能力就当无限豁免。实际策略有 best-effort 作用域局限。

### 沙箱路径与实际副作用

工具 handler 会初始化 provider，再检查路径并锁住文件操作。write_file 的本地路径验证与 file lock 写入，才是实际副作用路径。

Local sandbox 中的 host bash 另有准入函数；配置里出现 bash 不能单独证明它可调用。排查权限时，应追具体 handler 和执行环境，而不是只看工具描述。

源码观察：Local sandbox 下的 host bash 由独立准入函数控制，不能仅因有 bash 配置就认为可用。

`backend/packages/harness/deerflow/tools/tools.py:153-157`

```
    # Do not expose host bash by default when LocalSandboxProvider is active.
    if not is_host_bash_allowed(config):
        tool_configs = [tool for tool in tool_configs if not _is_host_bash_tool(tool)]

    loaded_tools_raw = [(cfg, resolve_variable(cfg.use, BaseTool)) for cfg in tool_configs]
```

源码观察：write_file 实际初始化 sandbox，验证 local 路径并经 file lock 写入。

`backend/packages/harness/deerflow/sandbox/tools.py:2943-2955`

```
    try:
        requested_path = path
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            validate_local_tool_path(path, thread_data)
            if not _is_custom_mount_path(path):
                path = _resolve_and_validate_user_data_path(path, thread_data)
            # Custom mount paths are resolved by LocalSandbox._resolve_path()
        with get_file_operation_lock(sandbox, path):
            sandbox.write_file(path, content, append)
        return "OK"
```

预测：传入其它 thread 的 host outputs 路径，不能只依赖哪个前端选择来保证隔离？

参考：前端选择不保证授权。runtime 的 user/thread、local 路径映射与验证、实际 handler gate 必须确认；具体 sandbox/network 隔离由 provider 与部署决定。

### 产物登记与内容验收

write_file 负责写入 bytes，present_files 负责登记产物。后者检查实际路径是否位于当前 thread 的 outputs 根，再返回 Command 更新 artifacts 及对应 ToolMessage。

产物出现在登记列表里，说明路径被报告给了界面；内容是否完整、是否满足用户要求仍需另外验收。也不能把登记步骤当作文件写入。

源码观察：present_files 的实际路径必须位于当前 thread 的 outputs 根。

`backend/packages/harness/deerflow/tools/builtins/present_file_tool.py:75-80`

```
    try:
        relative_path = actual_path.relative_to(outputs_dir)
    except ValueError as exc:
        raise ValueError(f"Only files in {OUTPUTS_VIRTUAL_PREFIX} can be presented: {filepath}") from exc

    return f"{OUTPUTS_VIRTUAL_PREFIX}/{relative_path.as_posix()}"
```

源码观察：present_files 返回 Command 更新 artifacts 和对应 ToolMessage，不负责文件写入。

`backend/packages/harness/deerflow/tools/builtins/present_file_tool.py:115-121`

```
    # The merge_artifacts reducer will handle merging and deduplication
    return Command(
        update={
            "artifacts": normalized_paths,
            "messages": [ToolMessage("Successfully presented files", tool_call_id=tool_call_id)],
        },
    )
```

预测：present_files 成功能否证明 summary.md 写过且内容正确？需要什么附加证据？

参考：不能。登记 Command 只规范化/约束路径与更新 artifacts；需读取文件、验证实际存在和内容/格式，下载还经过 Gateway 权限。

### 子代理双身份

子代理有两种调用身份。provider call id 关联公开工具请求，服务端 execution UUID 拥有后台执行；前者另存为 external_task_id。

task tool 用 provider tool_call_id 关联提案，用返回的 execution_id 控制后台工作。task_started 使用 provider ID，随后查询结果使用 execution ID。追委派时把两者并排记录，避免拿展示身份查询执行状态。

源码观察：server UUID 拥有后台 execution，provider task id 单独保留为 external_task_id。

`backend/packages/harness/deerflow/subagents/executor.py:2042-2050`

```
        execution_id = str(uuid.uuid4())

        # Create initial pending result
        result = SubagentResult(
            task_id=execution_id,
            external_task_id=task_id,
            trace_id=self.trace_id,
            status=SubagentStatus.PENDING,
        )
```

源码观察：task tool 以 provider tool_call_id 做关联，却用返回 execution_id 控制后台工作。

`backend/packages/harness/deerflow/tools/builtins/task_tool.py:995-997`

```
    # Keep the provider tool-call ID for stream/message correlation, but use a
    # server-generated execution ID for process-wide background task control.
    execution_id = executor.execute_async(prompt, task_id=tool_call_id)
```

源码观察：task_started 使用 provider ID，服务端随后使用 execution ID 查询结果。

`backend/packages/harness/deerflow/tools/builtins/task_tool.py:1014-1025`

```
        await aemit_custom_event(
            {
                "type": "task_started",
                "task_id": tool_call_id,
                "description": description or prompt,
                "model_name": effective_model,
            },
            writer=writer,
        )

        while True:
            result = get_background_task_result(execution_id)
```

预测：R1/R2 都有 call_7，registry、SSE、ledger 分别使用什么键？

参考：registry/cancel/poll 使用不同 execution UUID；task_* 与 ToolMessage 用各自 provider call_7；ledger 用 parent run_id+call_7。前端/事件查询还要保留 owning Run。

### 委派账本终态单调性

委派账本按 (run_id, id) 合并更新，并保留同一调用的顺序。已有终态不会被后来到达的非终态覆盖。

例如完成后才收到 started，状态不应退回运行中。判断是否属于同一次委派要结合 run 和 id；只按 id 合并可能混入另一轮执行。

源码观察：委派按 (run_id, id) 合并，非终态不能覆盖已有终态。

`backend/packages/harness/deerflow/agents/thread_state.py:206-215`

```
    for entry in [*(existing or []), *new]:
        entry_id = entry["id"]
        key = (entry.get("run_id") or None, entry_id)
        if key[0] is None:
            # Legacy updates without run_id still update the most recent
            # matching entry, as they did before run-scoped identities.
            key = next((prior for prior in reversed(order) if prior[1] == entry_id), key)
        previous = by_key.get(key)
        if previous is not None and previous["status"] in TERMINAL_STATUSES and entry["status"] not in TERMINAL_STATUSES:
            continue
```

预测：completed 后迟到 running，另一个 Run 同 call ID running，结果怎样？终态对终态呢？

参考：同 Run 保留 completed，另 Run 新增独立记录；reducer 仅拒绝终态→非终态，不保证终态→终态完全不变。

### 每轮、每 Run 与容量预算

task 调用同时受每轮并发上限和当前 Run 剩余总量约束，裁剪时取 remaining_total 与 max_concurrent 的较小值。缺少 run id 时采用限制性统计。

这描述的是委派预算。应用实际执行容量另有契约，不能只根据模型这一轮提出多少调用判断后台能够接纳多少工作。

源码观察：每轮并发上限与当前 Run 剩余总量共同裁剪 task 调用；缺 run id 采取限制性统计。

`backend/packages/harness/deerflow/agents/middlewares/subagent_limit_middleware.py:142-154`

```
        run_id = _runtime_run_id(runtime)
        if run_id is None:
            logger.warning("Subagent limit middleware received no run_id; counting all thread delegations as prior usage. Pass run_id in runtime context to enforce the total cap per run.")
        prior_delegation_count = _count_prior_delegations(state.get("delegations"), run_id=run_id)
        remaining_total = max(0, self.max_total - prior_delegation_count)
        allowed_task_calls = min(self.max_concurrent, remaining_total)

        if len(task_indices) <= allowed_task_calls:
            return None

        # Build set of indices to drop (excess task calls beyond the limit)
        indices_to_drop = set(task_indices[allowed_task_calls:])
        truncated_tool_calls = [tc for i, tc in enumerate(tool_calls) if i not in indices_to_drop]
```

预测：并发2、总量6、当轮已用5，新增3，保留多少？same-run continuation 和新 Run 如何区别？

参考：保留1；same-run continuation 不重置 ledger 计数；新 user Run 新 run_id。有缺失 run_id 的限制性 fallback，应用容量不是此公式的同义词。

### 压缩、最新请求与摘要字段

摘要先确定最新真实 user message 的 ID，在分区后保留当前请求；没有可摘要消息时跳过。成功压缩会替换 active messages，将摘要写入独立 summary_text，并按结果记录 task_history。

DurableContext 通过隐藏 HumanMessage 临时注入具体数据，request.override 不会写回 checkpoint 消息。排查恢复输入时，要分别看活动消息、摘要字段和临时请求数据。

源码观察：摘要确定最新真实 user message ID，在分区后救回当前请求；没有可摘要消息时跳过。

`backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py:603-613`

```
        latest_user_id: str | None = None
        for msg in reversed(messages):
            if is_genuine_user_message(msg):
                latest_user_id = msg.id
                break

        messages_to_summarize, preserved_messages = self._partition_messages(messages, cutoff_index)
        messages_to_summarize, preserved_messages = self._preserve_required_context(messages_to_summarize, preserved_messages, latest_user_id=latest_user_id)
        if not messages_to_summarize:
            return None
        return messages_to_summarize, preserved_messages, previous_summary, total_tokens
```

源码观察：成功压缩替换 active messages，摘要写独立 summary_text，按结果写 task_history。

`backend/packages/harness/deerflow/agents/middlewares/summarization_middleware.py:757-768`

```
    def _maybe_summarize(self, state: AgentState, runtime: Runtime) -> dict | None:
        result = self.compact_state(state, runtime, force=False)
        if result is None:
            return None
        return {
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                *result.preserved_messages,
            ],
            "summary_text": result.summary_text,
            **({"task_history": result.task_history} if result.task_history is not None else {}),
        }
```

源码观察：具体 durable data 进入隐藏 HumanMessage；request.override 不写回 checkpoint 消息。

`backend/packages/harness/deerflow/agents/middlewares/durable_context_middleware.py:439-449`

```
                HumanMessage(
                    content=data_block,
                    additional_kwargs={
                        "hide_from_ui": True,
                        _DURABLE_CONTEXT_DATA_KEY: True,
                        **provenance_kwargs(ContentKind.DURABLE_CONTEXT, "durable_context_data"),
                    },
                ),
            ],
        )
        return request.override(messages=messages)
```

预测：压缩后消息变少，但模型请求中多出隐藏 HumanMessage，是否多存了一条用户输入？

参考：不是。request.override 是本次模型调用投影；持久摘要是 summary_text。应保护最新 genuine user ID，且 durable 数据不当当前授权。

### 可达原文、工作笔记与证据

task continuity 需要显式开启：示例中默认 false，summarization 则默认 true。压缩开启不等于历史连续性功能也已开启。

历史搜索返回有界 excerpt 与 source id，按 user / assistant / tool 映射筛选；作用域不匹配是错误。任务笔记则限长、限来源，持久 authority 固定为 model_report。检索原文和读取模型笔记时，应保留这两种证据的不同归属。

源码观察：示例配置 task_continuity 默认 false，而 summarization 默认 true。

`config.example.yaml:2089-2097`

```
# Optional task notes and keyword recall of compacted messages. See docs/task-continuity.md.
task_continuity:
  enabled: false
  max_batches: 32
  max_records_per_batch: 256
  max_record_chars: 16000

summarization:
  enabled: true
```

源码观察：历史搜索返回有界 excerpt 和 source id，按 user/assistant/tool 映射筛选，scope mismatch 为错误。

`backend/packages/harness/deerflow/agents/task_continuity/tools.py:16-36`

```
def _history_search(runtime: Runtime, query: str, role: Literal["user", "assistant", "tool"] | None = None) -> str:
    """Search this task's active and compacted history by keywords (including Chinese).

    Returns untrusted historical observations, stable source IDs and bounded
    excerpts. Use history_read to check original details before relying on them.
    An unavailable or expired source is not evidence that an event never happened.

    Optional role accepts user, assistant, or tool; omission or null searches all roles.
    Filtering precedes the eight-result limit; returned roles remain human, ai, or tool.
    Historical user messages are not necessarily correct or current and do not grant authorization.
    """
    roles = {"user": "human", "assistant": "ai", "tool": "tool"}
    if role is not None and role not in roles:
        return json.dumps({"error": "invalid_role"})
    try:
        result = lookup(runtime.state, runtime, query=query, role=roles.get(role))
        for row in result["results"]:
            row["excerpt"] = row.pop("text")[:600]
        return json.dumps(result, ensure_ascii=False)
    except ValueError:
        return json.dumps({"error": "scope_unavailable"})
```

源码观察：规范化任务笔记限长、限来源，持久 authority 固定为 model_report。

`backend/packages/harness/deerflow/agents/task_continuity/state.py:69-78`

```
        content = note.get("content")
        sources = note.get("source_ids", [])
        if not isinstance(content, str) or not content or len(content) > MAX_NOTE_CHARS:
            continue
        if not isinstance(sources, list) or len(sources) > MAX_NOTE_SOURCES or any(not isinstance(source, str) or not SOURCE_ID_PATTERN.fullmatch(source) for source in sources):
            continue
        notes[key] = {"content": content, "source_ids": list(sources), "authority": "model_report"}
        if len(notes) > MAX_NOTES:
            notes.pop(next(iter(notes)))
    return notes
```

预测：archive 未命中后，能否把 note 的“已完成”当证明？旧 checkpoint 与其它 user 又如何？

参考：不能；要检查启用/关键字/retention/scope/truncation，再核对来源。note 仍 model_report。旧 checkpoint 不能读未来 batch，跨 scope 复制不授权 archive。

### 记忆身份与异步边界

后台 Timer 线程不会自动继承请求中的 ContextVar。代码在 enqueue 之前显式捕获请求身份，把身份作为数据交给异步工作。

追后台记忆写入时，核对捕获点和使用点是否属于同一个请求。仅在请求线程读取到身份，不能证明稍后运行的线程仍有相同上下文。

源码观察：请求身份在 enqueue 前显式捕获，避免定时线程丢失 ContextVar。

`backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py:175-187`

```
        # Capture user_id at enqueue time while the request context is still alive.
        # threading.Timer fires on a different thread where ContextVar values are not
        # propagated, so we must store user_id explicitly in ConversationContext.
        user_id = resolve_runtime_user_id(runtime)
        # The memory update fires on a threading.Timer thread that inherits no
        # ContextVars, so the id is captured here, while the request context is
        # still alive, and carried as data. The runtime context is authoritative
        # (worker._bind_trace_id always fills it); the ambient fallback covers
        # embedded callers driving the agent outside a Gateway run.
        runtime_context = runtime.context if isinstance(runtime.context, dict) else {}
        trace_id = resolve_trace_id(runtime_context.get(DEERFLOW_TRACE_METADATA_KEY))

        return thread_id, self._redact_queued_messages(messages), user_id, trace_id
```

预测：若在 Timer 回调中取当前 user，可能发生什么？如何取证？

参考：可能无用户或错误 bucket；应在 request 活着时捕获 user_id/agent_name/trace_id 并传给 manager。验证需两用户隔离对照，不能只看 memory.json 存在。

### 测试源码与真实运行证据

本案例区分测试源码、独立教学模拟、生产确定性 graph 与真实模型部署。当前仅阅读相关仓库测试，没有执行它们。

这些测试分别描述摘要遗漏后的 archive 检索、复制 state 的 scope 拒绝、旧 checkpoint 不读未来 batch，以及五次恢复后抛错时六次 stream calls 与五次 state reads 的预期。引用这些断言可以解释契约，不能报告为本次运行通过。

源码观察：仓库测试独立断言摘要遗漏某标识时，仍可由 archive 检索原始来源；本次仅阅读测试。

`backend/tests/test_task_continuity.py:49-57`

```
def test_compaction_preserves_exact_source_and_excludes_it_from_summary(scoped):
    state = {"messages": conversation()}
    update = compacting(TaskContinuityConfig(enabled=True))._maybe_summarize(state, scoped)
    assert update is not None
    assert "ZX-731" not in update["summary_text"]
    after = {**state, **update, "messages": list(update["messages"])[1:]}
    result = archive.lookup(after, scoped, query="Citrine")
    assert result["results"][0]["text"].endswith("决策保留备份。")
    assert result["results"][0]["id"] == archive.records(conversation())[0]["id"]
```

源码观察：仓库测试把复制 state 的 scope 拒绝与旧 checkpoint 不读未来 batch 作为独立用例；本次未执行。

`backend/tests/test_task_continuity.py:79-91`

```
def test_copied_checkpoint_cannot_read_another_scope(scoped, context):
    history = archive.capture({}, scoped, conversation(), TaskContinuityConfig(enabled=True))
    foreign = SimpleNamespace(context=context)
    result = archive.lookup({"task_history": history}, foreign, query="Citrine")
    assert result == {"results": [], "status": "scope_unavailable"}


def test_old_checkpoint_cannot_see_future_batch(scoped):
    config = TaskContinuityConfig(enabled=True)
    old = {"task_history": archive.capture({}, scoped, conversation(), config)}
    archive.capture(old, scoped, [HumanMessage(content="future secret ORCHID", id="future")], config)
    assert not archive.lookup(old, scoped, query="ORCHID")["results"]
    assert archive.lookup(old, scoped, query="Citrine")["results"]
```

源码观察：仓库测试期望五次恢复后抛错，对应六次 stream calls 与五次 state reads；本次未执行。

`frontend/tests/unit/core/api/api-client.test.ts:1059-1072`

```
  const consume = async () => {
    for await (const entry of getAPIClient(true).runs.joinStream(
      "thread-gap-loop",
      "run-gap-loop",
      { lastEventId: "1-0" },
    )) {
      // Drain until the recovery budget is exhausted.
      void entry;
    }
  };

  await expect(consume()).rejects.toBeInstanceOf(StreamReplayGapError);
  expect(streamCalls).toBe(6);
  expect(stateCalls).toBe(5);
```

预测：本教程 demo 5/5，能否说 DeerFlow 生产恢复已验证？列出缺什么。

参考：不能。demo 独立简化，只覆盖教学不变量；还需实际 production graph/StreamBridge、真实存储/多 worker/取消、model/tool 服务等对应实验。仓库测试仅阅读不能写执行通过。

### 从闭卷解释到受控扩展

合上正文，用真实源码解释输入、状态字段和失败路径，再设计一个迁移样例。网页访问和阅读进度不能单独证明已经理解。

复述时尤其要区分运行终态与研究验收：Run 终态结合 delivery_error 并记录 stop_reason，这些字段交代执行结果，仍不能判定报告结论是否正确。

源码观察：ThreadState 将消息之外的目标、委派、Skill、任务笔记和摘要分成独立状态字段。

`backend/packages/harness/deerflow/agents/thread_state.py:352-369`

```
class ThreadState(AgentState):
    sandbox: SandboxStateField
    thread_data: NotRequired[ThreadDataState | None]
    title: NotRequired[str | None]
    artifacts: Annotated[list[str], merge_artifacts]
    todos: Annotated[list | None, merge_todos]
    goal: Annotated[GoalState | None, merge_goal]
    uploaded_files: NotRequired[list[dict] | None]
    viewed_images: Annotated[dict[str, ViewedImageData], merge_viewed_images]  # image_path -> metadata (no base64)
    promoted: Annotated[PromotedTools | None, merge_promoted]
    delegations: Annotated[list[DelegationEntry], merge_delegations]
    skill_context: Annotated[list[SkillEntry], merge_skill_context]
    tool_artifacts: Annotated[list[ArtifactEntry], merge_tool_artifacts]
    tool_artifact_processed: Annotated[list[str], merge_artifacts]
    task_notes: Annotated[dict | None, TaskNotesChannel(dict | None, merge_task_notes)]
    task_history: NotRequired[dict | None]
    summary_text: NotRequired[str | None]
    background_tasks: NotRequired[list[BackgroundTaskState]]
```

源码观察：Run 终态结合 delivery_error，并记录 stop_reason；这不验收研究结论。

`backend/packages/harness/deerflow/runtime/runs/worker.py:1515-1522`

```
            delivery_error = _delivery_error(delivery_content)
            cancel_action = await run_manager.set_status_if_not_cancelled(
                run_id,
                RunStatus.error if delivery_error else RunStatus.success,
                error=delivery_error,
                stop_reason=stop_reason,
                **terminal_status_kwargs,
            )
```

预测：新增 citations_checked，先定义哪些契约？怎样避免模型自报被当框架 verdict？

参考：先定义 trusted producer、user/thread/run identity、初始值、merge/replay/retention、checkpoint/event 归属，再定义 HTTP admission 防伪造与 UI reducer；用正常、重复、迟到、旧 checkpoint、gap reload、跨用户对照。

### 闭卷复述与迁移

给出一个回放缺口和一个迟到委派事件，说明前端或账本应怎样处理。

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## Inspect AI · 任务执行之后，怎样判断结果

任务执行之后，怎样判断结果

来源：https://github.com/UKGovernmentBEIS/inspect_ai

提交：`e4b8ad59d8468d41cd5df844ec7100c7a1569cb1`；访问：2026-10-02

证据：独立教学模型3组固定正/错误策略对照；不导入上游，不构成生产Runtime验证。

原教学模型不替代真实 grader、Docker 或模型实验；准确率必须保留有效分母。

排除：真实模型与供应商质量；真实沙箱/鉴权与部署；跨进程持久恢复及外部副作用恰好一次；并发压力与生产竞态；学习者实际作答及掌握度

### 本案例阅读任务

从 Task 装配追到求解、评分与 EvalLog，解释分数对应哪些实际样本。

读前准备：第 7 章；能阅读 Python 函数。target 是评分依据，不能默认作为求解器的输入。

1. 分别定位 Dataset、Solver、Scorer 和 Sandbox。
2. 追 Agent 适配、submit 协议、grader 结果和 unscored。
3. 核对日志状态、计划/完成/记录数，再说明 accuracy 的分母。

检验理解：grader 输出无法解析时，为什么不能直接把这个样本记作 incorrect？

判断标准：区分评分协议失败和合法错误答案；报告有效评分数、未评分原因及计划范围。

阅读主线：从 Task、Solver、审批和 Sandbox 到 Scorer、EvalLog，区分正确、错误与未评分。

### 命令入口与参数装配

安装映射把 inspect 指向 CLI main，命令组再注册 eval 等子命令。入口存在只说明命令可发现；样本实际执行还要经过 Task 加载与运行调度。

找不到命令、参数错误和模型失败不属于同一层。先保存 CLI 参数和加载错误，不要通过改 Task Prompt 解决环境映射问题。包版本与源码 SHA 也必须在评测口径里固定。

源码观察：白话翻译
        安装包把终端里的 inspect 指向 inspect_ai._cli.main 模块中的 main()。先有这个映射，后面才谈得上 eval 子命令。

`pyproject.toml:186-187`

```
[project.scripts]
inspect = "inspect_ai._cli.main:main"
```

预测：inspect命令找不到，先修改Solver合适吗？

参考：不合适。先查安装入口与环境路径；能进入eval后再查参数、Task加载和Solver。

### 命令组与单次执行分开

main 注册 eval/log/view 等命令并初始化异常与环境行为；它不实现每个样本的解题循环。CLI 层的责任是把可复现配置传给公共入口。

参数默认值发生变化可能让同名任务跑出不同实验。记录最终 ResolvedTask 比只保存用户敲下的命令更可靠，因为配置、默认模型与角色仍可能在下游补齐。

源码观察：白话翻译
        主入口把 eval、log、view 等子命令挂到同一个 Click 命令组，然后初始化异常处理与环境变量。这里负责“有哪些线路”，不是执行样本。

`src/inspect_ai/_cli/main.py:43-62`

```
inspect.add_command(acp_command)
inspect.add_command(cache_command)
inspect.add_command(ctl_command)
inspect.add_command(download_command)
inspect.add_command(eval_command)
inspect.add_command(eval_set_command)
inspect.add_command(eval_retry_command)
inspect.add_command(info_command)
inspect.add_command(list_command)
inspect.add_command(log_command)
inspect.add_command(score_command)
inspect.add_command(view_command)
inspect.add_command(sandbox_command)
inspect.add_command(trace_command)


def main() -> None:
    set_exception_hook()
    init_dotenv()
    inspect(auto_envvar_prefix="INSPECT")  # pylint: disable=no-value-for-parameter
```

预测：相同CLI字符串是否保证两次评测相同？

参考：不保证。还需冻结版本、解析后的模型/角色、Task参数、数据、Sandbox、Solver和Scorer配置。

### eval与eval-set的生命周期

普通评测进入 eval，eval-set 还组织重试与恢复策略。重新安排任务不等于改变 Agent 求解器；但会改变运行数量和样本的实际覆盖。

分析成功率时不能把重试挑出的最好结果与单次结果直接比较。要说明每个实例的尝试数、最终采用规则、失败和日志归属，再归因模型或系统变化。

源码观察：白话翻译
        命令层把公共参数组装成 params。若是 Eval Set，走带重试与恢复配置的路径；普通单次评测则调用 eval(**params)。

`src/inspect_ai/_cli/eval.py:2161-2185`

```
    # evaluate
    if is_eval_set:
        params["retry_attempts"] = retry_attempts
        params["retry_immediate"] = retry_immediate
        params["retry_wait"] = retry_wait
        params["retry_connections"] = retry_connections
        params["retry_cleanup"] = retry_cleanup
        params["incomplete_action"] = incomplete_action
        params["incomplete_max"] = incomplete_max
        params["bundle_dir"] = bundle_dir
        params["bundle_overwrite"] = bundle_overwrite
        params["embed_viewer"] = embed_viewer
        params["log_dir_allow_dirty"] = log_dir_allow_dirty
        params["eval_set_id"] = eval_set_id
        if json_output:
            return _eval_exec_json(lambda: eval_set(**params), is_eval_set=True)
        success, _ = eval_set(**params)
        return success
    else:
        params["log_header_only"] = True  # cli invocation doesn't need full log
        if json_output:
            _eval_exec_json(lambda: (True, eval(**params)))
        else:
            eval(**params)
        return True
```

预测：启用eval-set重试后准确率提高，能直接称模型变强吗？

参考：不能。重试与选择策略改变了实验条件；先对齐样本、尝试次数和聚合规则，再做受控比较。

### Sample的输入与target

官方 Skills 示例并列保存 input 和 target。input 提供求解任务，target 是评分依据，不能默认认为 target 已经进入 Agent 提示。

把 target 泄漏给求解器会污染评测。审查时检查消息生成、Solver 和 Scorer 各自访问什么数据；训练式示例与真正评分样本的界限必须明确。

源码观察：白话翻译
        @task 让加载器能发现这个工厂函数。每个 Sample 把用户输入和评分目标并列保存；目标是判卷依据，不会自动变成给 Agent 的提示。

`examples/skills/task.py:26-51`

```
@task
def skills_example() -> Task:
    """Demonstrate agent skills for Linux system exploration."""
    return Task(
        dataset=[
            Sample(
                input="What Linux distribution is this system running? Include the version.",
                target="The system is running Ubuntu 24.04",
            ),
            Sample(
                input="How many CPU cores does this system have?",
                target="The number of CPU cores available on the system",
            ),
            Sample(
                input="What is the total amount of memory (RAM) on this system?",
                target="The total RAM available on the system",
            ),
            Sample(
                input="What is the IP address of this system?",
                target="The IP address(es) configured on the system's network interfaces",
            ),
            Sample(
                input="How much disk space is available on the root filesystem?",
                target="The available disk space on the root (/) filesystem",
            ),
        ],
```

预测：Agent碰巧输出target，如何排除答案泄漏？

参考：核对实际模型输入、Solver变换与工具可访问文件；target在样本存在不等于可见，必须用输入证据排除泄漏。

### Task装配四个独立职责

Task 将四项职责组合起来：Dataset 提供题目，Solver 执行求解，Scorer 判断结果，Sandbox 提供执行环境。示例中的 ReAct、Skills/Bash、模型评分和 Docker 分别参与这些环节，不能互相替代。

Docker 不会批准工具，Scorer 不会约束 Bash，Prompt 也不是隔离设置。修改实验前明确改变哪一项、保持哪几项不变，否则无法解释分数差异。

源码观察：白话翻译
        ReAct Agent 被要求先查 Skill，再用 Bash；model_graded_qa() 负责判卷；Docker Compose 提供每个样本运行的环境。四者各司其职。

`examples/skills/task.py:52-69`

```
        solver=react(
            prompt="You are a Linux system administrator. You have access to skills "
            "that provide guidance for system exploration tasks. Use the skill "
            "tool to get instructions before attempting tasks, then use bash "
            "to execute the appropriate commands.",
            tools=[
                skill(
                    [
                        SKILLS_DIR / "system-info",
                        SKILLS_DIR / "network-info",
                        SKILLS_DIR / "disk-usage",
                    ]
                ),
                bash(),
            ],
        ),
        scorer=model_graded_qa(),
        sandbox=("docker", "compose.yaml"),
```

预测：更换Sandbox但保持Prompt不变，实验是否无变化？

参考：有变化。环境资源、依赖和访问范围可能改变结果；需记录Sandbox配置与运行证据，并保持其他变量可比较。

### 从工厂到ResolvedTask

Loader 把工厂、参数、模型角色、Sandbox 与顺序解析为具体 Task。源码函数名不是完整实验身份；同一工厂可通过参数产生不同任务。

复现必须保存解析后的执行对象关键配置、数据版本和样本 ID。动态加载失败发生在求解前，不应作为模型答错计入 accuracy。

源码观察：白话翻译
        加载器把任务参数、来源文件、模型、角色、沙箱与顺序全部解析进 ResolvedTask。从这一刻起，调度器拿到的是具体执行单，而不是模糊配置。

`src/inspect_ai/_eval/loader.py:101-124`

```
    def as_resolved_tasks(tasks: list[Task]) -> list[ResolvedTask]:
        # shuffle data in tasks if requested
        if sample_shuffle:
            for task in tasks:
                if not task.dataset.shuffled:
                    task.dataset.shuffle(
                        None if sample_shuffle is True else sample_shuffle
                    )

        return [
            ResolvedTask(
                id=uuid(),
                task=task,
                task_args=resolve_task_args(task),
                task_file=task_file(task, relative=True),
                model=task.model or model,
                model_roles=_merge_model_roles(task.model_roles, model_roles),
                sandbox=resolve_task_sandbox(task, sandbox),
                checkpoint=task.checkpoint,
                sequence=sequence,
                input_media_policy=input_media_policy,
            )
            for sequence, task in enumerate(tasks)
        ]
```

预测：加载失败应该记为模型incorrect吗？

参考：不应混为一谈。记录加载/环境错误及未运行样本，评分只处理其协议定义下的有效答案。

### Agent到Solver的适配

Task 接受 Solver 列表、Agent 或 Solver 对象；Agent 通过 as_solver 转接。适配器负责把 TaskState 消息交给 AgentState，再将输出带回评测。

Agent 执行成功不保证适配返回的 completion 正确。调试空答案应同时检查 Agent 事件和 TaskState.output，而不是只看工具日志。

源码观察：白话翻译
        列表会串成 Solver chain；Agent 会走 as_solver()；已经是 Solver 的对象保持原样。转接在 Task 解析时发生。

`src/inspect_ai/_eval/task/task.py:636-642`

```
def resolve_solver(solver: Solver | Agent | list[Solver]) -> Solver:
    if isinstance(solver, list):
        return chain(solver)
    elif is_agent(solver):
        return as_solver(solver)
    else:
        return cast(Solver, solver)
```

预测：工具执行有结果，但Scorer拿到空completion，查哪里？

参考：查as_solver的消息/输出回写、异常路径与Agent是否提交；工具输出存在不能替代Solver答案。

### 异常时的现场保存

适配器使用 finally 尽量把 Agent 消息和输出交回 TaskState，保留失败现场供日志与评分查看。保存现场不等于把失败运行标为正确。

求解异常、部分输出、可评分答案和评测状态应分别保存。保留原错误与 partial trace，避免用空答案覆盖故障现场；若 Scorer 会评分部分结果，也要在实验定义里明确。

源码观察：白话翻译
        适配器把 Task 的消息放进 AgentState，运行 Agent，再把消息与输出写回 TaskState。即使发生异常，finally 也尽量保留可记录、可评分的现场。

`src/inspect_ai/agent/_as_solver.py:62-82`

```
    @solver
    def agent_to_solver() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            agent_state = AgentState(messages=state.messages)

            try:
                # run the agent with limits
                with apply_limits(limits):
                    async with span(name=agent_name, type=AGENT_SPAN_TYPE):
                        agent_state = await agent(agent_state, **agent_kwargs)
            # if an exception occurs, we still want to update the TaskState with the
            # AgentState's messages + output so that it appears in the log and is scored
            finally:
                # update messages
                state.messages = agent_state.messages

                # update output if its not empty
                if agent_state.output:
                    state.output = agent_state.output

            return state
```

预测：异常后仍有output字段，能标完成吗？

参考：不能仅凭字段存在。检查错误、submit状态、评分资格和日志计数；部分现场用于诊断，不自动成为有效成功样本。

### submit与普通文本的退出协议

ReAct 可循环生成与执行工具，成功 submit 工具结果才抽取答案，尝试上限和评分反馈控制继续。输出一句结论未必是提交完成。

退出原因会影响成本和样本有效性。要记录尝试数、限制、submit 失败及最终采用答案。到达上限也不是业务答案正确，应交给独立 Scorer 和日志判断。

源码观察：白话翻译
        成功的 submit Tool Result 被抽成答案并写入输出。达到最大尝试数，或中间评分成功，循环才结束；否则还可能带反馈继续下一次尝试。

`src/inspect_ai/agent/_react.py:294-327`

```
                                # check for a submission
                                answer = submission(messages)
                                if answer is not None:
                                    # set the output to the answer for scoring
                                    if submit.answer_only:
                                        state.output.completion = answer
                                    else:
                                        state.output.completion = f"{state.output.completion}{submit.answer_delimiter}{answer}".strip()

                                    # also populate the message text (as the submit tool will be removed)
                                    if (
                                        not submit.keep_in_messages
                                        and len(state.output.choices) > 0
                                    ):
                                        message = state.output.choices[0].message
                                        if isinstance(message.content, str):
                                            message.content = f"{message.content}{submit.answer_delimiter}{answer}".strip()
                                        else:
                                            message.content.append(
                                                ContentText(text=answer)
                                            )

                                    # exit if we are at max_attempts
                                    attempt_count += 1
                                    if attempt_count >= attempts.attempts:
                                        break

                                    # exit if the submission is successful
                                    answer_scores = await score(state)
                                    if (
                                        attempts.score_value(answer_scores[0].value)
                                        == 1.0
                                    ):
                                        break
```

预测：模型说“完成了”但没有成功submit，如何解释？

参考：这只是模型文字；核对submit调用、工具结果与Agent输出。退出协议和Scorer评分必须分别验收。

### 沙箱创建与清理

Sandbox 初始化样本 ID、文件和 setup，在 yield 期间运行样本，finally 负责清理并处理取消。每题隔离资源与清理寿命，是可复现环境的重要部分。

清理代码存在不能证明容器实际成功退出或挂载安全。需要真实环境日志、资源检查和失败注入；本课只读取路径，不启动 Docker。

源码观察：白话翻译
        环境初始化时带入样本 ID、文件和 setup；yield 期间真正运行样本；无论正常结束还是取消，finally 都负责清理，并对中断清理做 shield。

`src/inspect_ai/_eval/task/sandbox.py:145-178`

```
        interrupted = False
        environments: dict[str, SandboxEnvironment] | None = None
        try:
            # initialize sandbox environment
            metadata = dict(sample.metadata) if sample.metadata else {}
            metadata["__sample_id__"] = sample.id

            environments = await init_sandbox_environments_sample(
                sandboxenv_type=sandboxenv_type,
                task_name=registry_unqualified_name(task_name),
                config=sandbox.config,
                files=files,
                setup=setup,
                metadata=metadata,
            )

            # run sample
            yield

        except anyio.get_cancelled_exc_class() as ex:
            interrupted = True
            raise ex

        finally:
            # cleanup sandbox environment
            if environments and cleanup:
                with anyio.CancelScope(shield=interrupted):
                    await cleanup_sandbox_environments_sample(
                        type=sandbox.type,
                        task_name=task_name,
                        config=sandbox.config,
                        environments=environments,
                        interrupted=interrupted,
                    )
```

预测：取消后Docker仍运行，能用finally存在证明已清理吗？

参考：不能。检查实际清理结果、取消屏蔽与资源状态；源码控制结构只是意图与路径，不能替代运行观察。

### 没有审批与没有匹配策略

先看是否注册 approver。没有注册时，apply_approval 允许调用；启用 policy 后，未匹配的请求则被拒绝。两个结果来自不同配置，报告默认行为时必须同时写出配置状态。

Docker 隔离和 approval 决策相互独立。测试至少包括未配置、配置且匹配允许、配置但无匹配；每个结果保存有效策略，才能排除环境默认的混淆。

源码观察：白话翻译
        有 approver 时，决策可以批准、修改、拒绝或终止；没有任何审批系统注册时，函数明确返回允许。是否在 Docker 里运行不会改变这条逻辑。

`src/inspect_ai/approval/_apply.py:48-71`

```
        # call approver (approvers which use model inference — e.g. LLM monitors —
        # shouldn't have that inference charged to the agent's own budget)
        with suspend_token_limit(), suspend_turn_limit():
            approval = await approver(
                message=message,
                call=call,
                view=view,
                history=history,
            )

        # process decision
        match approval.decision:
            case "approve" | "modify":
                return True, approval
            case "reject":
                return False, approval
            case "terminate":
                return False, approval
            case "escalate":
                raise RuntimeError("Unexpected 'escalate' from policy approver.")

    # no approval system registered
    else:
        return True, None
```

预测：policy开启后工具无匹配，应当继承未配置时allow吗？

参考：不应。当前启用policy的未匹配路径拒绝；先区分是否注册审批与已注册策略的匹配结果。

### 批准、修改、拒绝与终止

审批可以改变参数、拒绝一次调用或终止运行。批准最终参数与模型提出参数可能不同，审计必须保留两者及决策。

一次允许不自动覆盖后续所有操作；评分正确也不撤销越权行为。授权来自应用策略与审批者，Tool 描述及模型建议不提供授权。

源码观察：白话翻译
        一旦启用 policy approver，调用必须匹配某条工具策略并得到非 escalate 决策；没有匹配者时反而拒绝。别混淆“未启用审批”和“已启用但未匹配”。

`src/inspect_ai/approval/_policy.py:67-82`

```
        # process approvers for this tool call (continue loop on "escalate")
        has_approver = False
        for approver in tool_approvers(call):
            has_approver = True
            approval = await call_approver(approver, message, call, view, history)
            if approval.decision != "escalate":
                return approval

        # if there are no approvers then we reject
        reject = Approval(
            decision="reject",
            explanation=f"No {'approval granted' if has_approver else 'approvers registered'} for tool {call.function}",
        )
        # record and return the rejection
        record_approval("policy", message, call, view, reject)
        return reject
```

预测：审批者改了命令，日志应保存什么？

参考：保存原提议、修改后的执行参数、审批决策与实际工具结果，再关联样本和调用身份；不能只保留模型原文。

### grader是另一阶段模型

Scorer 把问题/历史、completion、target 和说明填入模板，再调用 grader。求解模型与判卷模型可能不同，成本、版本与失败各自归属。

grader 看见 target 是正常评分过程，但它的输出还需要严格解析。评价质量不能只看求解模型版本；提示、grader 和 reducer 都可能造成分数漂移。

源码观察：白话翻译
        评分器选择当前问题或完整历史，把 Agent 输出、target、说明和元数据填入模板，再调用 grader 模型。这个调用与 Agent 求解请求是不同阶段。

`src/inspect_ai/scorer/_model.py:283-312`

```
    async def score(state: TaskState, target: Target) -> Score:
        # resolve model
        nonlocal model
        model = model if isinstance(model, Model) else get_model(model)

        # metadata without grading template variables
        metadata = omit(
            state.metadata, ["question", "answer", "criterion", "instructions"]
        )

        # present the question
        if include_history is True:
            question = chat_history(state)
        elif callable(include_history):
            question = include_history(state)
        else:
            question = state.input_text

        # format the scoring template
        scoring_prompt = model_scoring_prompt(
            template=grading_template,
            question=question,
            output=state.output,
            criterion=target.text,
            instructions=instructions,
            metadata=metadata,
        )

        # query the model for the score
        result = await model.generate([scoring_prompt])
```

预测：只换grader后分数提高，可归因Solver吗？

参考：不能。冻结或单独比较grader、评分模板与聚合规则；Solver质量与判卷变化需要独立对照。

### 非法grade与incorrect分开

解析只接受约定的 grade；非法、多字符或无法解析的结果返回带 grader_failed 原因的 unscored。未评分不是合法 incorrect。

把全部 grader 失败记成 0 会混合基础设施/协议和能力差异。应同时报告有效评分数、错误数、计划数和采用的缺失处理口径。教学正反例将检验这一边界。

源码观察：白话翻译
        解析器只接受约定 grade。多字符异常值或不在可选集合中的结果被视为协议偏差；代码返回带 grader_failed 原因的 unscored Score，而不是偷偷记为 incorrect。

`src/inspect_ai/scorer/_model.py:314-360`

```
        # extract the grade
        match = re.search(resolved_grade_pattern, result.completion)
        value = match.group(1) if match else None
        if value is not None and default_grade_pattern:
            # The permissive capture takes the whole word so that "GRADE:
            # Correct"/"GRADE: Incorrect"/"GRADE: Partial" keep resolving to
            # their letter. A multi-character verdict that is not one of the
            # spelled-out grades (e.g. "GRADE: CI") is a protocol deviation,
            # not evidence about the submission, so it is a parse failure
            # rather than a silently laundered first letter.
            normalized = value.strip().lower()
            if normalized in _GRADE_WORD_VALUES:
                value = _GRADE_WORD_VALUES[normalized]
            elif len(value.strip()) == 1:
                value = value.strip().upper()
            else:
                value = None
            if validate_offered_grades and value not in offered_grades:
                # A verdict outside the grades the instructions offered is a
                # protocol deviation, not evidence about the submission, so it
                # is a scoring failure rather than an incorrect answer.
                value = None
        if value is not None:
            return Score(
                value=value,
                answer=state.output.completion,
                explanation=result.completion,
                metadata=dict(
                    grading=[
                        scoring_prompt,
                        result.message,
                    ]
                ),
            )
        else:
            return Score.unscored(
                reason="grader_failed",
                answer=state.output.completion,
                explanation="Grade not found in model output: "
                + f"{result.completion}",
                metadata=dict(
                    grading=[
                        scoring_prompt,
                        result.message,
                    ],
                ),
            )
```

预测：grader返回UNKNOWN，应直接记I吗？

参考：先按评分协议标为unscored/grader_failed，保留原因；只有预先冻结的缺失策略可影响聚合，不能悄悄当成答错。

### metric值与样本分母

默认 accuracy 把 C/I/P/N 映射为 1/0/0.5/0，再对收到的分数求平均。空分数集合返回 0 时，应先说明没有有效输入，不能把它解释成完整评测的 0%正确。

聚合值依赖传入集合；部分取消、未评分和多个 attempt 会改变分母。报告必须写有效样本数与处理规则，否则单个 accuracy 没有可比较意义。

源码观察：白话翻译
        默认映射是 C=1、I=0、P=0.5、N=0，再对传入分数求平均。没有分数时返回 0；解读报告时仍要同时查看已完成、已记录和未评分样本数。

`src/inspect_ai/scorer/_metrics/accuracy.py:14-37`

```
@metric
def accuracy(to_float: ValueToFloat = value_to_float()) -> Metric:
    r"""Compute proportion of total answers which are correct.

    Args:
       to_float: Function for mapping `Value` to float for computing
          metrics. The default `value_to_float()` maps CORRECT ("C") to 1.0,
          INCORRECT ("I") to 0, PARTIAL ("P") to 0.5, and NOANSWER ("N") to 0,
          casts numeric values to float directly, and prints a warning and returns
          0 if the Value is a complex object (list or dict).

    Returns:
       Accuracy metric
    """

    def metric(scores: list[SampleScore]) -> float:
        if not scores:
            # No scores to average; return 0 rather than dividing by zero,
            # mirroring the insufficient-data guards in std()/var().
            return 0.0
        total = 0.0
        for item in scores:
            total += to_float(item.score.value)
        return total / float(len(scores))
```

预测：计划100题只完成10题，accuracy=0.9可以说90题正确吗？

参考：不能。应报告有效计分10题及其9题正确，并另外给出计划/完成/未评分/错误计数；不得把比例乘错分母。

### EvalSpec使差异可归因

EvalSpec 保存 Task 身份、参数、模型、样本 ID、Solver、Scorer、Metric、Sandbox、revision 与包版本。这些字段把一次分数变成可复核实验。

只保存最终表格会丢掉最容易造成回归的变量。比较前先列不变项与变更项，再确认两边数据截止与尝试规则相同。

源码观察：白话翻译
        EvalSpec 保存任务身份与参数、Solver、模型、数据集及样本 ID、Scorer、Metric、Sandbox、运行配置、源码 revision 和包版本。没有这些，分数差异很难归因。

`src/inspect_ai/_eval/task/log.py:280-319`

```
        # create eval spec
        self.eval = EvalSpec(
            eval_set_id=eval_set_id,
            run_id=run_id,
            created=iso_now(),
            task=f"{task_name}",
            task_id=task_id if task_id else uuid(),
            task_version=task_version,
            task_file=task_file,
            task_registry_name=task_registry_name,
            task_display_name=task_display_name,
            task_attribs=task_attribs,
            task_args=task_args,
            task_args_passed=task_args_passed,
            solver=solver.solver if solver else None,
            tags=tags,
            solver_args=solver.args if solver else None,
            solver_args_passed=solver.args_passed if solver else None,
            model=f"{ModelName(model).api}/{model.name}",
            model_generate_config=model.config,
            model_base_url=model.explicit_base_url,
            model_roles=model_roles_to_model_roles_config(model_roles),
            dataset=EvalDataset(
                name=dataset.name,
                location=cwd_relative_path(dataset.location),
                samples=len(dataset),
                sample_ids=sample_ids,
                shuffled=dataset.shuffled,
            ),
            scorers=eval_scorers,
            metrics=eval_metrics,
            headline_metric=headline_metric,
            sandbox=sandbox,
            model_args=model_args,
            config=eval_config,
            revision=revision,
            packages=packages,
            metadata=metadata,
            viewer=viewer,
        )
```

预测：两份结果只写模型名和accuracy，下一步是什么？

参考：补齐Task/样本/版本/Solver/Scorer/Sandbox/限制与尝试参数，确认可比后再讨论回归。

### 日志状态不是答案准确率

顶层 status 描述评测生命周期；samples/results/stats/error 分别记录答案、统计和故障，invalidated 说明结果可用性。一次 success 的评测仍可能全部答错，因此它不等于 accuracy=1。

完整运行可全部答错；运行失败也可能有部分正确样本。字段顺序还属于格式兼容责任，不应为方便而随意修改序列化形状。

源码观察：白话翻译
        顶层 status 不等于 accuracy；error、invalidated、samples、results 与 stats 各自回答不同问题。字段顺序还是日志格式的一部分，修改需要升版本并同步读写逻辑与测试。

`src/inspect_ai/log/_log.py:1218-1265`

```
class EvalLog(BaseModel):
    """Evaluation log."""

    # WARNING: The order of these fields is important for the log file format.
    # Do not change the order of these fields without incrementing the version number,
    # updating the log file read/write functionality (such as read_eval_log),
    # and updating the tests.
    version: int = Field(default=2)
    """Eval log file format version."""

    status: EvalStatus = Field(default="started")
    """Status of evaluation (did it succeed or fail)."""

    eval: EvalSpec
    """Eval identity and configuration."""

    plan: EvalPlan = Field(default_factory=EvalPlan)
    """Eval plan (solvers and config)"""

    results: EvalResults | None = None
    """Eval results (scores and metrics)."""

    stats: EvalStats = Field(default_factory=EvalStats)
    """Eval stats (runtime, model usage)"""

    error: EvalError | None = Field(default=None)
    """Error that halted eval (if status=="error")"""

    invalidated: bool = Field(default=False)
    """Whether any samples were invalidated."""

    log_updates: list[LogUpdate] | None = Field(default=None)
    """Post-eval edits to tags and metadata."""

    config_updates: list[ConfigUpdate] | None = Field(default=None)
    """Mid-run configuration changes applied via the control channel (`inspect ctl config`)."""

    tags: list[str] = Field(default_factory=list)
    """Current tags (eval-time + edits). Do not set directly; use edit_eval_log()."""

    metadata: dict[str, Any] = Field(default_factory=dict)
    """Current metadata (eval-time + edits). Do not set directly; use edit_eval_log()."""

    samples: list[EvalSample] | None = Field(default=None)
    """Samples processed by eval."""

    reductions: list[EvalSampleReductions] | None = Field(default=None)
    """Reduced sample values"""
```

预测：status=success但accuracy低，是自相矛盾吗？

参考：不是。生命周期成功表示评测完成，accuracy表示答案结果；二者应一起报告，且保留样本数和评分有效性。

### 完成、记录与计划计数

total_samples 是计划数，completed_samples 强调无错误完成，取消/drain 时 logged_samples 说明实际解决并记录的范围。三种数目不可互换。

迁移到自建回归系统前，先冻结有效样本判定与缺失处理规则，再实现计数。本课的源码阅读和独立教学模型没有生成真实 Eval Log，真实 grader 质量和 Docker 行为仍未验证。

源码观察：白话翻译
        total_samples 是计划数；completed_samples 是无错误完成数；取消或 drain 时，logged_samples 还会指出本日志真正解决了多少。只看总数会把中途放弃误读成完整运行。

`src/inspect_ai/log/_log.py:848-871`

```
class EvalResults(BaseModel):
    """Scoring results from evaluation."""

    total_samples: int = Field(default=0)
    """Total samples in eval (dataset samples * epochs)"""

    completed_samples: int = Field(default=0)
    """Samples completed without error.

    Will be equal to total_samples except when --fail-on-error is enabled
    or when there is early stopping.
    """

    logged_samples: int | None = Field(default=None)
    """Samples this log actually resolved (present in the log and not
    cancelled), when a graceful task cancel or drain abandoned queued samples.

    `total_samples` records the *planned* count, so a log finished by
    `inspect ctl task drain` or `inspect ctl task cancel --action score|error`
    would otherwise read complete to an eval set; the eval set's run-vs-reuse
    check prefers this count when present so the abandoned remainder is
    re-run by a later invocation. None on ordinary logs (and logs written by
    older versions), which classify by `total_samples` as before.
    """
```

预测：迁移回归报告，最重要的计数不变量是什么？

参考：计划、已记录、完成、有效评分与失败分别计数，任何比例写明分母；先验证取消和grader失败案例，再比较两个版本。

### 闭卷复述与迁移

grader 输出无法解析时，为什么不能直接把这个样本记作 incorrect？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## Codex 上下文压缩 · 压缩后下一次请求读到什么

压缩后下一次请求读到什么

来源：https://github.com/openai/codex

提交：`551844b3efc426c563128b0e011e36dad95a865b`；访问：2026-10-02

证据：独立教学模型3组固定正/错误策略对照；不导入上游，不构成生产Runtime验证。

仅限上下文压缩专题；历史重放和当前运行兼容性状态保持原结论。

排除：真实模型与供应商质量；真实沙箱/鉴权与部署；跨进程持久恢复及外部副作用恰好一次；并发压力与生产竞态；学习者实际作答及掌握度

### 本案例阅读任务

追踪/compact 如何选择策略并安装替代历史，解释恢复后下一次请求采用哪个窗口。

读前准备：第 2、6 章；能阅读 Rust 枚举、Result 和分支。replacement_history 是用于替换旧窗口的历史记录。

1. 从 TUI 操作追到 CompactTask，确认策略优先级与触发方式。
2. 区分单个 OutputItemDone 和整体 Completed，再追窗口安装与持久化。
3. 用最新 replacement_history 及后续条目预测恢复输入，核对历史兼容边界。

检验理解：已有摘要文字但没有 Completed 时，为什么不能接受为成功压缩？

判断标准：说明请求完成、response 身份和持久化阶段的证据；历史 replay 不能替代当前二进制的新运行。

阅读主线：沿 /compact、压缩策略、Completed、replacement history、checkpoint 和 resume 追踪窗口身份。

### UI 命令只建立入口

/compact 的说明文字和菜单描述不是压缩算法。真正路径从 TUI 分派到 Session 操作，再进入 CompactTask。

先标输入、操作消息、任务与模型调用四个边界，才能解释 spinner 为什么转但历史还未变。页面出现压缩提示不证明持久 checkpoint 已经接受。

源码观察：白话翻译
        /compact 被描述成“总结会话”，但这句话没有承诺逐字保留所有历史，也没有说明由本地模型、远端服务还是 token-budget 机制执行。实现细节要继续往下追。

`codex-rs/tui/src/slash_command.rs:86-94`

```
impl SlashCommand {
    /// User-visible description shown in the popup.
    pub fn description(self) -> &'static str {
        match self {
            SlashCommand::Feedback => "send logs to maintainers",
            SlashCommand::New => "start a new chat during a conversation",
            SlashCommand::Init => "create an AGENTS.md file with instructions for Codex",
            SlashCommand::Compact => "summarize conversation to prevent hitting the context limit",
            SlashCommand::Recap => "summarize the current conversation now",
```

预测：看到“压缩中”，能断言旧窗口已被替换吗？

参考：不能。UI只说明操作过程；检查策略完成、checkpoint与历史安装的事件或状态。

### 交互限制与状态清理

TUI 对任务状态做前置判断，清理显示用 usage 并更新状态，再发出压缩操作。界面计数变化属于显示状态，不等于模型上下文立即改变。

诊断时区分 UI 缓存和 core 历史。将 token 显示归零当预算已释放会把观察层与状态层混为一谈；需要看核心新窗口和基线。

源码观察：白话翻译
        若输入由父任务接管，命令当场拒绝。否则 TUI 清空展示中的 token 用量、点亮运行与状态指示、标记下一回合待开始，最后才通过事件通道发出 compact 请求。

`codex-rs/tui/src/chatwidget/slash_dispatch.rs:294-312`

```
            SlashCommand::Compact => {
                if self.blocks_direct_input {
                    self.add_error_message(PARENT_OWNED_INPUT_MESSAGE.to_string());
                    return;
                }
                self.clear_token_usage();
                if !self.bottom_pane.is_task_running() {
                    self.bottom_pane.set_task_running(/*running*/ true);
                }
                self.bottom_pane.ensure_status_indicator();
                self.set_status(
                    compaction::COMPACTION_HEADER.to_string(),
                    Some(compaction::COMPACTION_DETAILS.to_string()),
                    StatusDetailsCapitalization::Preserve,
                    STATUS_DETAILS_DEFAULT_MAX_LINES,
                );
                self.input_queue.user_turn_pending_start = true;
                self.app_event_tx.compact();
            }
```

预测：usage显示被清零，可否报告压缩成功？

参考：不能。还要验证core完成事件、replacement_history和当前窗口安装；显示状态不是持久状态。

### 压缩任务替换旧任务

Session 处理压缩操作时中止原任务并以新 turn context 启动 CompactTask。任务被替换与当前对话历史被摘要是两个独立动作。

外部任务可能已产生副作用，中止不能回滚这些动作。读到 Replaced 一类原因时，别误归为模型质量失败；它描述调度生命周期。

源码观察：白话翻译
        压缩不是塞进正在运行的旧 turn。handler 先以 Replaced 原因中止旧任务，再用默认设置建立新 turn，并把 CompactTask 交给 session 调度。

`codex-rs/core/src/session/handlers.rs:243-251`

```
pub async fn compact(sess: &Arc<Session>, sub_id: String) {
    // Stop the old turn before the compact task picks up the next turn's environments.
    sess.abort_all_tasks(TurnAbortReason::Replaced).await;
    let turn_context = sess
        .new_turn_with_default_settings(sub_id, Default::default())
        .await;

    sess.spawn_task(turn_context, Vec::new(), CompactTask).await;
}
```

预测：旧任务收到Replaced，就说明摘要失败吗？

参考：不一定。旧任务被新操作替换属于调度；压缩任务本身是否完成要看后续策略和持久化结果。

### 策略分派有优先级

CompactTask 先按配置选择 TokenBudget，其次 RemoteV2，否则走本地摘要。分支会早返回，追一次操作时应确认实际选中了哪条策略。

冻结版本与 feature 配置非常关键：仅记录“用了 compact”无法比较实现。名字相似的功能可能采用不同输入、输出和网络路径。

源码观察：白话翻译
        TokenBudget 优先并提前返回；否则 capability 为 V2 就交给远端；不支持远端才合成 compact prompt，进入本地摘要实现。

`codex-rs/core/src/tasks/compact.rs:35-68`

```
        let _profile_guard = ctx.turn_timing_state.begin_compaction();
        if ctx.config.features.enabled(Feature::TokenBudget) {
            crate::compact_token_budget::run_manual_compact_task(session, ctx).await?;
            return Ok(None);
        }

        let result = match ctx.provider.capabilities().remote_compaction {
            RemoteCompactionSupport::V2 => {
                emit_compact_metric(
                    &session.services.session_telemetry,
                    "remote_v2",
                    /*manual*/ true,
                );
                crate::compact_remote_v2::run_remote_compact_task(session.clone(), ctx).await
            }
            RemoteCompactionSupport::Unsupported => {
                emit_compact_metric(
                    &session.services.session_telemetry,
                    "local",
                    /*manual*/ true,
                );
                let input = vec![UserInput::Text {
                    text: ctx
                        .config
                        .compact_prompt
                        .as_deref()
                        .unwrap_or(crate::compact::SUMMARIZATION_PROMPT)
                        .to_string(),
                    // Compaction prompt is synthesized; no UI element ranges to preserve.
                    text_elements: Vec::new(),
                }];
                crate::compact::run_compact_task(session.clone(), ctx, input).await
            }
        };
```

预测：同时打开两个feature，是否会先裁剪再摘要？

参考：应按当前代码分派顺序与early return判断；不能凭配置名推导串联。记录实际选中策略。

### 预算裁剪没有摘要也属于压缩

TokenBudget 使用公共任务生命周期，但策略不必生成自然语言摘要。读压缩路径时，先看它改变了哪些保留项，再检查是否生成 summary。

评估信息损失要对照保留项、移除项与恢复窗口，而不是只检查摘要质量。功能配置、二进制 schema 兼容和运行成功也必须分开记录。

源码观察：白话翻译
        它仍发出共同的 compaction lifecycle 与 turn item，方便 hooks 和观察层保持一致；但“同生命周期”不代表“同摘要语义”。这里根本没有生成 summary。

`codex-rs/core/src/compact_token_budget.rs:19-36`

```
/// Runs token-budget manual compaction as a normal compaction lifecycle.
///
/// Token-budget compaction skips model/server summarization and installs a fresh context window
/// instead. It is still modeled as compaction so compact hooks and `ContextCompaction` turn items
/// observe the same lifecycle as local or remote compaction.
pub(crate) async fn run_manual_compact_task(
    sess: Arc<Session>,
    turn_context: Arc<TurnContext>,
) -> CodexResult<()> {
    sess.emit_turn_started(&turn_context).await;

    // Manual compaction runs outside run_turn, so it captures its own current step.
    let step_context = sess
        .capture_step_context(Arc::clone(&turn_context), &CancellationToken::new())
        .await?;
    let world_state = Arc::new(sess.build_world_state_for_step(&step_context).await?);
    run_compact_task_inner(&sess, &step_context, world_state, CompactionTrigger::Manual).await
}
```

预测：没有summary字段就能判压缩失败吗？

参考：不能。先确认策略是否为预算裁剪，再验证保留历史和窗口语义；摘要不是所有策略的必需产物。

### 自动触发与手动任务不同

自动压缩位于正常 turn 执行流程，使用类似策略优先级，但阶段与初始上下文注入条件不同。手动路径的结论不能无条件复制到自动路径。

设计比较时固定触发方式、压缩前 history、策略与注入模式；否则恢复后的差异可能来自上下文基线，而非摘要模型。

源码观察：白话翻译
        自动路径的优先级仍是 token-budget → remote v2 / local，但它还携带 reason、phase、fallback context 与 initial-context 注入策略。触发方式和实现方式是两个维度。

`codex-rs/core/src/session/turn.rs:1457-1503`

```
    if turn_context.config.features.enabled(Feature::TokenBudget) {
        // Compaction is the reset request, so force a new context window
        // instead of consuming a pending `new_context` tool request.
        crate::compact_token_budget::run_inline_auto_compact_task(
            Arc::clone(sess),
            step_context,
            initial_context_injection,
        )
        .await?;
        return Ok(());
    }

    match turn_context.provider.capabilities().remote_compaction {
        RemoteCompactionSupport::V2 => {
            emit_compact_metric(
                &sess.services.session_telemetry,
                "remote_v2",
                /*manual*/ false,
            );
            run_inline_remote_auto_compact_task_v2(
                Arc::clone(sess),
                step_context,
                fallback_step_context,
                client_session,
                initial_context_injection,
                reason,
                phase,
            )
            .await?;
        }
        RemoteCompactionSupport::Unsupported => {
            emit_compact_metric(
                &sess.services.session_telemetry,
                "local",
                /*manual*/ false,
            );
            run_inline_auto_compact_task(
                Arc::clone(sess),
                Arc::clone(turn_context),
                initial_context_injection,
                reason,
                phase,
            )
            .await?;
        }
    }
    Ok(())
```

预测：手动测试通过就覆盖自动compact了吗？

参考：没有。触发时点和注入条件可能不同；分别固定输入history与配置，验证各自新窗口和后续请求。

### 手动摘要输入从历史快照构造

本地路径克隆 history 并加入专门输入，处理不同消息形态及已执行工具调用。它不是对 TUI 可见文字直接做字符串摘要。

注入模式控制独立摘要任务的上下文构造。调查漏记工具结果时应检查模型实际收到的请求，而不是只看滚动终端。

源码观察：白话翻译
        live history 先克隆，再追加合成的 compact 输入；真正送模前还会按模型输入模态裁剪，并附上已执行工具调用。重试复用同一个 client session，以保住 turn-scoped 状态。

`codex-rs/core/src/compact.rs:257-300`

```
    let compaction_item = TurnItem::ContextCompaction(ContextCompactionItem::new());
    sess.emit_turn_item_started(&turn_context, &compaction_item)
        .await;
    let initial_input_for_turn: ResponseInputItem = ResponseInputItem::from(input);

    let mut history = sess.clone_history().await;
    history.record_items(
        &[initial_input_for_turn.into()],
        turn_context.model_info().truncation_policy.into(),
    );

    let max_retries = turn_context.provider.info().stream_max_retries();
    let mut retries = 0;
    let mut client_session = sess.services.model_client.new_session();
    // Reuse one client session so turn-scoped state (sticky routing, websocket incremental
    // request tracking)
    // survives retries within this compact turn.
    let responses_metadata = sess
        .compaction_responses_metadata(turn_context.as_ref(), compaction_metadata)
        .await;

    let compaction_response = loop {
        // Clone is required because of the loop
        let mut turn_input = history
            .clone()
            .for_prompt(&turn_context.model_info().input_modalities);
        sess.services
            .executed_tool_calls
            .attach_to_compaction_prompt(&mut turn_input);
        let turn_input_len = turn_input.len();
        let prompt = Prompt {
            input: turn_input,
            base_instructions: sess.get_prompt_base_instructions().await,
            ..Default::default()
        };
        let attempt_result = drain_to_completed(
            &sess,
            turn_context.as_ref(),
            &mut client_session,
            &responses_metadata,
            &prompt,
            compaction_metadata.phase(),
        )
        .await;
```

预测：终端有工具输出，摘要模型一定看到了吗？

参考：不一定。核对history快照、消息转换与请求内容；UI文字和模型输入不完全等价。

### 失败分支需要保留原因

本地流处理区分任务中断、预算失败、上下文窗口超限与普通错误。窗口超限可触发历史调整重试，普通错误按策略退避。

删掉字段或随意缩输入让请求成功会改变冻结实验，不能冒充原方案通过。报告要保留初始失败、实际变更和比较范围。

源码观察：白话翻译
        中断、turn 被替换、预算耗尽都直接失败。只有 context window 超限时会逐个删最老 history item；普通 stream 错误则按 provider 的次数与退避策略重连。

`codex-rs/core/src/compact.rs:302-346`

```
        match attempt_result {
            Ok(response) => {
                break response;
            }
            Err(err)
                if matches!(
                    err.details(),
                    CodexErrorDetails::Interrupted | CodexErrorDetails::TurnAborted
                ) =>
            {
                return Err(err);
            }
            Err(e) if matches!(e.details(), CodexErrorDetails::SessionBudgetExceeded) => {
                return Err(e);
            }
            Err(e) if matches!(e.details(), CodexErrorDetails::ContextWindowExceeded) => {
                if turn_input_len > 1 {
                    // Trim from the beginning to preserve cache (prefix-based) and keep recent messages intact.
                    error!(
                        "Context window exceeded while compacting; removing oldest history item. Error: {e}"
                    );
                    history.remove_first_item();
                    retries = 0;
                    continue;
                }
                sess.set_total_tokens_full(turn_context.as_ref()).await;
                return Err(e);
            }
            Err(e) => {
                if retries < max_retries {
                    retries += 1;
                    let delay = backoff(retries);
                    sess.notify_stream_error(
                        turn_context.as_ref(),
                        format!("Reconnecting... {retries}/{max_retries}"),
                        e,
                    )
                    .await;
                    tokio::time::sleep(delay).await;
                    continue;
                } else {
                    return Err(e);
                }
            }
        }
```

预测：因schema不兼容失败，删字段后能报原策略通过吗？

参考：不能。新配置是另一实验。保留兼容性失败证据，明确变更后范围；0次请求也不能当模型运行。

### OutputItemDone 不是 Completed

OutputItemDone 表示单个输出项结束，整体请求还需要 Completed 及对应 response ID/usage。premature EOF 属于失败；已有摘要文字也不能替代请求完成信号。

这是恢复和计费边界：摘要内容可读不代表请求完整。教学对照会对“有文字但无 Completed”的流拒绝成功，避免把中间产物当正式压缩结果。

源码观察：白话翻译
        如果流先断，函数明确报错。OutputItemDone 只是中间产物；看到 Completed 后，代码记录 response ID 和用量，才返回可供下一阶段安装的 CompactionResponse。

`codex-rs/core/src/compact.rs:797-845`

```
    let mut output = Vec::new();
    loop {
        let maybe_event = stream.next().await;
        let Some(event) = maybe_event else {
            return Err(CodexErr::Stream(
                "stream closed before response.completed".into(),
            ));
        };
        match event {
            Ok(ResponseEvent::OutputItemDone(item)) => {
                if matches!(phase, CompactionPhase::PostTurn) {
                    // Commit post-turn summaries only after success; failures must leave both
                    // the live history and persisted rollout intact.
                    output.push(item);
                } else {
                    sess.record_conversation_items(
                        turn_context,
                        turn_context.model_info(),
                        std::slice::from_ref(&item),
                    )
                    .await;
                }
            }
            Ok(ResponseEvent::ServerReasoningIncluded(included)) => {
                sess.set_server_reasoning_included(included).await;
            }
            Ok(ResponseEvent::RateLimits(snapshot)) => {
                sess.update_rate_limits(turn_context, snapshot).await;
            }
            Ok(ResponseEvent::Completed {
                response_id,
                token_usage,
                usage_metadata,
                ..
            }) => {
                sess.record_observed_response_completed(
                    turn_context,
                    &response_id,
                    token_usage.as_ref(),
                    usage_metadata.as_ref(),
                )
                .await;
                sess.update_token_usage_info(turn_context, token_usage.as_ref())
                    .await?;
                return Ok(CompactionResponse {
                    response_id,
                    output,
                });
            }
```

预测：已有summary文字但连接EOF，可以安装新history吗？

参考：先按完整响应协议判断；没有所需Completed不能仅靠输出项接受成功。记录中断，保留旧已接受历史。

### 保留用户消息要排除旧摘要

构建替代历史时收集用户消息，区分压缩摘要标记与真实输入，并保留必要身份元信息。旧 summary 不能重新伪装成用户原文。

连续压缩的污染风险在于层层摘要当事实重复累积。追踪时给真实用户、压缩结果和工具观察分标签，检查每种记录进入新窗口的规则。

源码观察：白话翻译
        解析不成 UserMessage 的 item 被跳过；此前的 compaction summary 也明确排除，避免把旧摘要伪装成用户原话再重复装入。被选中的消息可携带 identity 与 metadata。

`codex-rs/core/src/compact.rs:578-600`

```
fn compacted_user_message(
    item: &ResponseItem,
    harness_metadata: Option<CodexHarnessMetadata>,
) -> Option<CompactedUserMessage> {
    let Some(TurnItem::UserMessage(user)) = crate::event_mapping::parse_turn_item(item) else {
        return None;
    };
    if is_summary_message(&user.message()) {
        return None;
    }
    Some(CompactedUserMessage {
        id: item.id().cloned(),
        message: user.message(),
        internal_chat_message_metadata_passthrough: match item {
            ResponseItem::Message {
                internal_chat_message_metadata_passthrough,
                ..
            } => internal_chat_message_metadata_passthrough.clone(),
            _ => None,
        },
        harness_metadata,
    })
}
```

预测：上次summary能当新一轮user消息再追加吗？

参考：应遵守压缩消息的专门过滤规则；不要把合成摘要当原始用户输入，保留类别与身份。

### 预算打包偏向较新用户消息

本地路径用固定预算从较新用户消息向前装入，必要时截断边界消息，再恢复时间顺序。保留顺序与截断策略是信息损失评估的具体对象。

这个机制不保证早期关键约束永不丢失。课程实验应把约束放在不同位置并测试恢复后可用性，不能从“保留用户消息”推导全量保真。

源码观察：白话翻译
        默认上限来自 COMPACT_USER_MESSAGE_MAX_TOKENS = 20_000。算法从最新消息倒序装箱；最后一条若放不下会按剩余额度截断，之后再反转回时间顺序。

`codex-rs/core/src/compact.rs:674-719`

```
pub(crate) fn build_compacted_history(
    initial_context: Vec<ResponseItemEnvelope>,
    user_messages: &[CompactedUserMessage],
    summary_text: &str,
) -> Vec<ResponseItemEnvelope> {
    build_compacted_history_with_limit(
        initial_context,
        user_messages,
        summary_text,
        COMPACT_USER_MESSAGE_MAX_TOKENS,
    )
}

fn build_compacted_history_with_limit(
    mut history: Vec<ResponseItemEnvelope>,
    user_messages: &[CompactedUserMessage],
    summary_text: &str,
    max_tokens: usize,
) -> Vec<ResponseItemEnvelope> {
    let mut selected_messages: Vec<CompactedUserMessage> = Vec::new();
    if max_tokens > 0 {
        let mut remaining = max_tokens;
        for message in user_messages.iter().rev() {
            if remaining == 0 {
                break;
            }
            let tokens = approx_token_count(&message.message);
            if tokens <= remaining {
                selected_messages.push(message.clone());
                remaining = remaining.saturating_sub(tokens);
            } else {
                let truncated =
                    truncate_text(&message.message, TruncationPolicy::Tokens(remaining));
                selected_messages.push(CompactedUserMessage {
                    id: message.id.clone(),
                    message: truncated,
                    internal_chat_message_metadata_passthrough: message
                        .internal_chat_message_metadata_passthrough
                        .clone(),
                    harness_metadata: message.harness_metadata.clone(),
                });
                break;
            }
        }
        selected_messages.reverse();
    }
```

预测：重要约束放在最早一条，是否一定完整保留？

参考：没有这种保证。核对预算、消息长度与截断边界，显式测早期约束及最近更正，不用自然语言概括代替验证。

### 不同策略替代历史形状不同

RemoteV2 对输入和元数据分组施加预算，再消费服务输出。读取结果形状时要单独追这条路径，不能沿用本地 user+summary 的假设；统一安装接口并未消除策略差异。

比较策略时应使用项类型、身份、窗口链与后续实际请求来评价。仅统计文本长度更短会错过保留约束、工具配对或多模态丢失。

源码观察：白话翻译
        remote v2 先把 input 与 metadata 重新配对、按 group 过滤，再用独立预算截断，最后追加 server 返回的 compaction output。它甚至单独统计保留图片，因此不能假设等同于 local 的“用户消息＋文字摘要”。

`codex-rs/core/src/compact_remote_v2.rs:505-532`

```
fn build_v2_compacted_history(
    prompt_input: Vec<ResponseItem>,
    prompt_input_metadata: Vec<Option<CodexHarnessMetadata>>,
    compaction_output: ResponseItem,
    retain_client_developer_messages: bool,
    image_budget: RetainedImageBudget,
) -> (Vec<ResponseItemEnvelope>, usize) {
    debug_assert_eq!(prompt_input.len(), prompt_input_metadata.len());
    let prompt_input = prompt_input
        .into_iter()
        .zip(prompt_input_metadata)
        .map(|(item, metadata)| ResponseItemEnvelope { item, metadata })
        .collect::<Vec<_>>();
    let retained = v2_history_item_groups(prompt_input)
        .filter(|group| {
            is_retained_for_remote_compaction_v2(&group.source, retain_client_developer_messages)
        })
        .flat_map(HistoryItemGroup::into_items)
        .collect::<Vec<_>>();
    let mut retained =
        truncate_retained_messages(retained, RETAINED_MESSAGE_TOKEN_BUDGET, image_budget);
    let retained_image_count = retained
        .iter()
        .map(|envelope| retained_input_image_count(&envelope.item))
        .sum::<usize>();
    retained.push(ResponseItemEnvelope::new(compaction_output));
    (retained, retained_image_count)
}
```

预测：两个策略token都减半，能认为等效吗？

参考：不能。比较保留项身份、约束、工具关系、窗口元数据及恢复后请求；缩短幅度只是一个指标。

### 窗口版本与上下文基线

压缩完成后推进窗口编号并按阶段设置初始上下文与基线。新窗口既有内容，也有版本与注入语义。

只保存 summary 字符串会丢掉恢复所需的窗口链。研究应标记压缩前后 window 身份、阶段和参考上下文，防止同一内容被错误注入两次。

源码观察：白话翻译
        builder 先推进窗口编号，按 phase 决定是否放入 initial context，再把 new_history、reference context、world-state baseline 与 response/model/window 元数据一起交给唯一安装入口。

`codex-rs/core/src/compact.rs:376-403`

```
    let (window_number, window_ids) = sess.advance_auto_compact_window().await;

    let (initial_context, world_state_baseline) =
        build_compaction_initial_context(sess.as_ref(), &initial_context_injection).await;
    if !initial_context.is_empty() {
        new_history =
            insert_initial_context_before_last_real_user_or_summary(new_history, initial_context);
    }
    let reference_context_item = match initial_context_injection {
        InitialContextInjection::DoNotInject => None,
        InitialContextInjection::BeforeLastUserMessage { step_context, .. } => {
            Some(step_context.to_turn_context_item())
        }
    };
    sess.replace_compacted_history(
        new_history,
        reference_context_item,
        world_state_baseline,
        CompactedHistoryMetadata {
            message: summary_text,
            window_number,
            window_ids,
            compaction_response_id: Some(compaction_response.response_id),
            compaction_model_hash: turn_context.model_info().comp_hash.clone(),
            reviewer_compaction_hash: None,
        },
    )
    .await;
```

预测：复制summary就足够建立新checkpoint吗？

参考：不够。还需replacement_history、窗口身份/链和上下文基线等协议元数据，按当前安装流程处理。

### 先统一记录身份再持久化

Session 为待保留项目补齐 ID，构造含 replacement_history 的新 CompactedItem，保存窗口、远程响应与其他状态。持久记录和内存安装应引用一致身份。

若重新生成不同 ID，恢复时去重、窗口引用和后缀关联可能断开。教学模型会比较链一致与错误改 ID，真实磁盘故障未在本包注入。

源码观察：白话翻译
        missing ID 在 clone 之前补齐，所以 live 与 persisted 两份 history 共享同一 identity。CompactedItem 不只存 message，还内嵌完整 replacement、窗口链、远端 response ID、MCP 来源和最近 token record。

`codex-rs/core/src/session/mod.rs:3936-3972`

```
    pub(crate) async fn replace_compacted_history(
        &self,
        mut items: Vec<ResponseItemEnvelope>,
        reference_context_item: Option<TurnContextItem>,
        world_state_baseline: Option<Arc<WorldState>>,
        metadata: CompactedHistoryMetadata,
    ) {
        for envelope in &mut items {
            Self::assign_missing_response_item_id(&mut envelope.item);
        }
        if let Some(checkpoint) = items.iter_mut().rev().find(|envelope| {
            matches!(
                envelope.item,
                ResponseItem::Compaction { .. } | ResponseItem::ContextCompaction { .. }
            )
        }) {
            checkpoint
                .metadata
                .get_or_insert_default()
                .compaction_model_hash = metadata.compaction_model_hash;
        }
        let mut compacted_item = CompactedItem {
            message: metadata.message,
            replacement_history: Some(items.clone()),
            retained_context: None,
            guardian_history: None,
            mcp_resource_origins: self.services.mcp_runtime.resource_origin_checkpoint(),
            window_number: Some(metadata.window_number),
            first_window_id: Some(metadata.window_ids.first_window_id.to_string()),
            previous_window_id: metadata
                .window_ids
                .previous_window_id
                .map(|id| id.to_string()),
            window_id: Some(metadata.window_ids.window_id.to_string()),
            compaction_response_id: metadata.compaction_response_id,
            latest_token_usage_record: self.state.lock().await.latest_token_usage_record.clone(),
        };
```

预测：持久化和内存各生成一组ID有问题吗？

参考：会破坏同一历史项的身份关联。按主线先统一身份，再让持久记录和活动history使用一致的ID及窗口链。

### 安装与hook有顺序边界

持久 checkpoint、内存历史替换、上下文基线、参考信息和 hook 位于同一完成链的不同阶段。hook 调用不等于每个后续行为都成功。

复盘失败必须指出最后可确认的阶段和恢复起点。不能看到一行 hook 日志就宣称整个持久化链通过；实际运行需关联同次压缩事件。

源码观察：白话翻译
        rollout 先记 Compacted checkpoint，再依次附带 baseline、reference context 与当前 settings 事件。持久化返回后，还排队一次来源为 Compact 的 session-start hook。

`codex-rs/core/src/session/mod.rs:3997-4013`

```
        let mut rollout_items = vec![RolloutItem::Compacted(compacted_item)];
        // Persist the baseline after the replacement history that established it.
        if let Some(world_state_item) = world_state_item {
            rollout_items.push(RolloutItem::WorldState(world_state_item));
        }
        if let Some(turn_context_item) = reference_context_item {
            rollout_items.push(RolloutItem::TurnContext(turn_context_item));
        }
        // The frozen turn context must not override current settings in persisted metadata.
        rollout_items.push(RolloutItem::EventMsg(
            thread_settings::applied_event(self).await,
        ));
        self.persist_rollout_items(&rollout_items).await;
        {
            let mut state = self.state.lock().await;
            state.queue_pending_session_start_source(codex_hooks::SessionStartSource::Compact);
        }
```

预测：hook日志存在能证明下次resume正确吗？

参考：不能。核对checkpoint内容、活动history与恢复重建；hook是生命周期观察，恢复正确性需单独验收。

### 恢复重建有明确输出

rollout 重建不只返回消息，还恢复上下文、设置、压缩基线和窗口链。正常 turn 入口使用这些结果构造新的运行环境。

把恢复简化为读 JSON 后拼文本会遗漏策略和注入状态。尤其连续压缩，必须知道当前窗口来自哪个 checkpoint。

源码观察：白话翻译
        返回值不只是 message list：retained/guardian context、previous settings、reference context、world-state baseline 和窗口链必须从同一次 replay 一起推导，避免各自指向不同时间点。

`codex-rs/core/src/session/rollout_reconstruction.rs:9-23`

```
// Return value of `Session::reconstruct_history_from_rollout`, bundling the rebuilt history with
// the resume/fork hydration metadata derived from the same replay.
#[derive(Debug)]
pub(super) struct RolloutReconstruction {
    pub(super) history: Vec<ResponseItemEnvelope>,
    pub(super) retained_context: codex_history::RetainedContext,
    pub(super) guardian_history: Option<codex_history::GuardianHistoryCheckpoint>,
    pub(super) previous_turn_settings: Option<PreviousTurnSettings>,
    pub(super) reference_context_item: Option<TurnContextItem>,
    pub(super) world_state_baseline: Option<WorldStateSnapshot>,
    pub(super) window_number: u64,
    pub(super) first_window_id: Option<Uuid>,
    pub(super) previous_window_id: Option<Uuid>,
    pub(super) window_id: Option<Uuid>,
}
```

预测：实现resume只返回消息列表够吗？

参考：对本课所追踪协议不够。还需基线、设置、参考上下文和窗口链，明确各自来源与兼容分支。

### 最近替代窗口加其后缀

重建从最新有效 replacement_history checkpoint 建立基线，再按边界处理后续 rollout。旧窗口不能无条件再次混入当前 history。

恢复窗口中出现更多文字，也可能是旧项混入。教学反例将压缩前条目追加回来，与期望窗口形成差异；这只验证独立模型，没有执行实际 Codex 进程。

源码观察：白话翻译
        遇到 CompactedItem 时恢复窗口链，并把“带 replacement_history 的第一个新 checkpoint”记作 base，同时保存它之后的 suffix。回滚语义还会决定哪些 segment 真正存活。

`codex-rs/core/src/session/rollout_reconstruction.rs:172-207`

```
        for (index, item) in rollout_items.iter().enumerate().rev() {
            match item {
                RolloutItem::Compacted(compacted) => {
                    let active_segment =
                        active_segment.get_or_insert_with(ActiveReplaySegment::default);
                    active_segment.world_state_replay.push(item);
                    if active_segment.window.is_none()
                        && let Some(window_number) = compacted.window_number
                    {
                        active_segment.window = Some(ReconstructedWindow {
                            number: window_number,
                            first_id: compacted.first_window_id.as_deref().and_then(parse_uuid_v7),
                            previous_id: compacted
                                .previous_window_id
                                .as_deref()
                                .and_then(parse_uuid_v7),
                            id: compacted.window_id.as_deref().and_then(parse_uuid_v7),
                        });
                    }
                    // Looking backward, compaction clears any older baseline unless a newer
                    // `TurnContextItem` in this same segment has already re-established it.
                    if matches!(
                        active_segment.reference_context_item,
                        TurnReferenceContextItem::NeverSet
                    ) {
                        active_segment.reference_context_item = TurnReferenceContextItem::Cleared;
                    }
                    if active_segment.base_compaction.is_none()
                        && compacted.replacement_history.is_some()
                    {
                        active_segment.base_compaction = Some(ReplayCheckpoint {
                            compacted,
                            suffix: &rollout_items[index + 1..],
                        });
                    }
                }
```

预测：旧rollout仍在磁盘，resume应全部拼回吗？

参考：不能。用最新有效替代历史作为当前基线，再追加适用后缀并处理回滚片段；旧窗口不是当前上下文。

### 旧格式兼容与新运行分开

重建保留 summary-only 等旧格式兼容路径。历史记录能成功解析与当前二进制能按相同配置发出新请求，是两种能力。

本课沿用已有历史 replay 和兼容性记录的口径。重新引用源码或运行教学模型，不会解除 frozen binary 缺失和 FeatureToml 兼容阻塞，也不足以证明后续实际模型请求正确。

源码观察：白话翻译
        旧 rollout 只有 summary message 时，源码明确承认 canonical context 的临时插入形状可能偏离分布。这是兼容路径，不是理想主路径。

`codex-rs/core/src/session/rollout_reconstruction.rs:382-393`

```
                RolloutItem::Compacted(compacted) => {
                    // Reverse replay already chose the newest surviving checkpoint. Any newer
                    // replacement checkpoint belongs to a rolled-back turn; replay its original
                    // items so the rollback can still find the removed user boundary.
                    if compacted.replacement_history.is_none() {
                        saw_legacy_compaction_without_replacement_history = true;
                        // Legacy rollouts without `replacement_history` should rebuild the
                        // historical TurnContext at the correct insertion point from persisted
                        // `TurnContextItem`s. These are rare enough that we currently just clear
                        // `reference_context_item`, reinject canonical context at the end of the
                        // resumed conversation, and accept the temporary out-of-distribution
                        // prompt shape.
```

预测：历史replay通过，能改标fresh runtime通过吗？

参考：不能。分别报告历史重建、分析器敏感性、二进制/schema兼容和fresh runtime；必须有真实新请求和完整运行证据才验后一层。

### 闭卷复述与迁移

已有摘要文字但没有 Completed 时，为什么不能接受为成功压缩？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## OpenAI Agents SDK · 谁拥有下一轮控制权

工具调用、handoff、最终输出和等待审批，如何变成不同的下一步？

来源：https://github.com/openai/openai-agents-python

提交：`a575a6e637feb9aea1b591237b007dd4991ddfba`；访问：2026-10-02

证据：本次完成源码阅读和摘录核验；未运行这个项目的模型、工具或服务。



排除：Realtime / Voice；Sandbox 的隔离实现；Provider 网络行为；完整 tracing 管线

### 本案例阅读任务

区分 run 中的继续、handoff、最终输出和审批等待，追踪当前 Agent 与输入如何变化。

读前准备：第 1、3、4 章；能阅读 Python 异步分支。guardrail 是应用配置的检查流程。

1. 先按公开入口理解 run 与模型 turn 的计数范围。
2. 追 current_agent 和交接输入，再检查最终输出与审批分支。
3. 核对会话保存条件与 max_turns，分别记录等待、失败和完成。

检验理解：handoff 后，原 Agent 是否继续主持，接收者是否一定看到全部前文？

判断标准：依据 current_agent 切换与输入过滤回答；专家作为工具的控制语义需要单独研究，审批恢复未运行。

阅读主线：Runner.run 接收起始 Agent 与输入 → AgentRunner 调用模型并解释响应 → NextStep 决定完成、交接、暂停或再运行 → 工具结果与会话条目按生命周期保存

### 一次调用与整个运行

把“帮用户查询订单，再说明结果”画成一次 run，里面可能有多次模型调用。模型先生成工具请求，程序执行请求，将结果放回输入，然后模型才能解释订单。这里的 run 是任务边界，turn 是一次模型调用口径；把两者混用，会同时误算成本和误设停止条件。

这段是公开入口的文档契约。它给出阅读地图；下面必须继续检查实际分支，才能判断当前实现是否遵守地图。final output 是按 Agent 的输出契约得到的结果，不能从字符串里出现“完成”两个字推导状态已经终止。handoff 则让另一个 Agent 成为当前执行者。

迁移到自己的系统时，先定义四种结果：继续、完成、等待、失败。不要让调用者猜测一个字符串究竟是答案、错误还是暂停提示。

源码观察：Runner 的契约把模型调用、工具继续和交接纳入一个运行循环。

`src/agents/run.py:278-292`

```

        The agent will run in a loop until a final output is generated. The loop runs like so:

          1. The agent is invoked with the given input.
          2. If there is a final output (i.e. the agent produces something of type
             `agent.output_type`), the loop terminates.
          3. If there's a handoff, we run the loop again, with the new agent.
          4. Else, we run tool calls (if any), and re-run the loop.

        In two cases, the agent may raise an exception:

          1. If the max_turns is exceeded, a MaxTurnsExceeded exception is raised unless handled.
          2. If a guardrail tripwire is triggered, the matching tripwire exception is raised,
             e.g. InputGuardrailTripwireTriggered or OutputGuardrailTripwireTriggered.

```

预测：订单查询工具返回了 JSON，run 就一定结束了吗？

参考：不一定。工具结果是后续输入；还要由下一步判定是否已形成最终输出，或需要再次调用模型。

### 交接改变当前 Agent

在客服场景中，普通工具像“帮我查一件事”；handoff 像“接下来的对话交给退款专员”。实际分支把 current_agent 换成 new_agent，并同时更新 starting_input 与 original_input。这意味着后续运行的指令、工具和输出契约可能变化。

交接后的输入来自 turn_result.original_input；代码注释明确说它可能已经嵌套或过滤。不能假定接收者总能看到逐字完整的前文，也不能把当前应用的 context 对象等同于模型可见消息。排查交接丢信息时，记录交接前后的输入差异和接收 Agent 名称，比只记录“发生了 handoff”有用。

若你的需求是让专家计算一个值，然后由原 Agent 继续主持，优先研究 Agent 作为工具的路线。本案例没有展开该路线的实现；两种控制权语义应分别验证。

源码观察：NextStepHandoff 替换 current_agent，并安装经过交接处理的输入。

`src/agents/run.py:2140-2151`

```
                        elif isinstance(turn_result.next_step, NextStepHandoff):
                            current_agent = cast(Agent[TContext], turn_result.next_step.new_agent)
                            if run_state is not None:
                                run_state._current_agent = current_agent
                            # Next agent starts with the nested/filtered input.
                            # Assign without type annotation to avoid redefinition error
                            starting_input = turn_result.original_input
                            original_input = turn_result.original_input
                            current_span.finish(reset_current=True)
                            current_span = None
                            should_run_agent_start_hooks = True
                        elif isinstance(turn_result.next_step, NextStepRunAgain):
```

预测：交接后忘记用户刚提供的限制，第一步查什么？

参考：查交接输入的过滤或嵌套结果、current_agent 与新的输入边界，而不是先假定模型没记住。

### 最终输出仍要过检查

出现最终候选输出后，程序先运行检查；检查拒绝时，不能仅因模型已经输出答案就提交成功。这里采用当前 Agent 的 output_guardrails 和运行配置中的检查；发生交接后，需要重新确认有效策略，不能直接套用起始 Agent 的全部规则。

Guardrail 是应用配置的判断函数及其处理流程。框架提供接口，并不意味着你的业务已经有正确规则。比如“订单号必须来自真实查询”需要业务证据验证；仅检查输出 JSON 格式，不能发现模型编造的订单状态。

本书据此提出一个设计判断：验收应放在终态提交之前，并保留拒绝的原因。这个判断是跨项目推理，不是声称所有框架天然具备同一套事务保证。

源码观察：最终输出分支会执行当前 Agent 与 RunConfig 的 output guardrails。

`src/agents/run.py:1915-1931`

```
                        if isinstance(turn_result.next_step, NextStepFinalOutput):
                            if run_state is not None and _has_output_guardrails(
                                current_agent, run_config
                            ):
                                run_state._tool_output_guardrail_results = list(
                                    tool_output_guardrail_results
                                )
                            output_guardrail_result_start = len(output_guardrail_results)
                            try:
                                await run_output_guardrails(
                                    current_agent.output_guardrails
                                    + (run_config.output_guardrails or []),
                                    current_agent,
                                    turn_result.next_step.output,
                                    context_wrapper,
                                    output_guardrail_results,
                                )
```

预测：结构化输出合法，能证明业务结果真实吗？

参考：不能。格式检查证明形状；真实性还需要与查询结果、权限和任务条件相对照。

### 能力发现与调用审批

一个工具可以在当前上下文中不可用，也可以可用但这次调用需要审批。is_enabled 决定启用状态；needs_approval 可以按参数和 call_id 决定某一次调用是否要暂停；输入和输出检查又是另一层。把它们都写成一个“安全开关”，会失去行为可解释性。

注释说明待批准调用通过 RunState.approve 或 reject 再继续。审批粒度涉及本次调用身份与参数，不能因为用户上次允许过一种工具，就推导新参数、新对象或新副作用已经获准。反过来，也不要让同一次已批准调用反复打断用户。

源码字段只证明机制存在。本次没有运行审批恢复，未证明重复工具调用不会造成重复写入；要验证后者，应由工具服务提供幂等键，并测试执行完成但回执丢失的路径。

源码观察：is_enabled、tool guardrails 与 needs_approval 是独立配置。

`src/agents/tool.py:485-507`

```
    is_enabled: bool | Callable[[RunContextWrapper[Any], AgentBase], MaybeAwaitable[bool]] = True
    """Whether the tool is enabled. Either a bool or a Callable that takes the run context and agent
    and returns whether the tool is enabled. You can use this to dynamically enable/disable a tool
    based on your context/state."""

    # Keep guardrail fields before needs_approval to preserve v0.7.0 positional
    # constructor compatibility for public FunctionTool callers.
    # Tool-specific guardrails.
    tool_input_guardrails: list[ToolInputGuardrail[Any]] | None = None
    """Optional list of input guardrails to run before invoking this tool."""

    tool_output_guardrails: list[ToolOutputGuardrail[Any]] | None = None
    """Optional list of output guardrails to run after invoking this tool."""

    needs_approval: (
        bool | Callable[[RunContextWrapper[Any], dict[str, Any], str], Awaitable[bool]]
    ) = False
    """Whether the tool needs approval before execution. If True, the run will be interrupted
    and the tool call will need to be approved using RunState.approve() or rejected using
    RunState.reject() before continuing. Can be a bool (always/never needs approval) or a
    function that takes (run_context, tool_parameters, call_id) and returns whether this
    specific call needs approval. For decorated Python tools, callable policies receive raw
    parsed arguments only when validation preserves their values, types, and dictionary order.
```

预测：工具已经启用，为什么还可能暂停等待用户？

参考：启用表示可以被选择；needs_approval 仍可能要求这次调用通过审批，二者的粒度和责任不同。

### 继续分支的保存边界

继续分支将本轮条目交给 save_turn_items_if_needed，再进入下一轮。是否保存还取决于 session、持久化开关、检查结果和 store 配置。读到这次函数调用后，需要继续追实际保存条件与结果，才能判断数据是否已持久化。

调试跨轮问题需要同时看模型输入、会话存储和 RunState。消息出现在 UI、消息已经传给模型、消息进入持久会话，是三个可以不同步的事实。只有把 response_id 与条目范围一起保存，才能定位重复保存或恢复时漏掉工具结果。

本案例只展示这一保存调用边界，没有证明某个数据库实现的原子性、跨进程锁或恢复一致性。选定 Session 实现后，还应做断开、重试和再次读取的测试。

源码观察：NextStepRunAgain 会先调用会话保存辅助函数，再继续循环。

`src/agents/run.py:2151-2163`

```
                        elif isinstance(turn_result.next_step, NextStepRunAgain):
                            await save_turn_items_if_needed(
                                session=session,
                                run_state=run_state,
                                session_persistence_enabled=session_persistence_enabled,
                                input_guardrail_results=input_guardrail_results,
                                items=session_items_for_turn(turn_result),
                                response_id=turn_result.model_response.response_id,
                                store=store_setting,
                                wrapper=context_wrapper,
                            )
                            continue
                        else:
```

预测：看到 save_turn_items_if_needed 被调用，就能报告数据库写入成功吗？

参考：不能。需要检查持久化条件、具体 Session 实现和实际写入/重读证据。

### 停止预算的计数口径

这里计数发生在模型轮次边界，而不是每一次函数工具执行。一次模型输出里可以出现多个工具请求；业务预算若按工具费用计算，不能直接用 max_turns 替代。计数变量与比较运算也要一起读，才能解释上限的边界。

max_turns 为 None 时这条比较不限制轮次。即使存在轮次上限，仍应另行控制墙钟时间、工具执行时间与取消信号；一次工具调用长时间不返回，不会因为下一轮尚未发生而自动消失。

读超限路径时继续查看错误处理器，避免把“形成异常”写成“所有场景必定直接抛给用户”。本摘录证明超限对象建立；具体处理与最终输出还取决于后续 handler。

源码观察：current_turn 增加后与 max_turns 比较，超限形成 MaxTurnsExceeded。

`src/agents/run.py:1506-1516`

```
                    current_turn += 1
                    if max_turns is not None and current_turn > max_turns:
                        _error_tracing.attach_error_to_span(
                            current_span,
                            SpanError(
                                message="Max turns exceeded",
                                data={"max_turns": max_turns},
                            ),
                        )
                        max_turns_error = MaxTurnsExceeded(f"Max turns ({max_turns}) exceeded")
                        run_error_data = build_run_error_data(
```

预测：三个工具请求出现在同一个模型响应里，必然消耗三次 max_turns 吗？

参考：不是；这里的 turn 按模型调用口径定义。工具次数、费用与超时需要独立计量。

### 闭卷复述与迁移

handoff 后，原 Agent 是否继续主持，接收者是否一定看到全部前文？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## smolagents · 把代码当作动作

模型写下的 Python 如何成为可观察的动作？错误又怎样进入下一轮？

来源：https://github.com/huggingface/smolagents

提交：`c30b115286e000e98711fae5e85993547b73d826`；访问：2026-10-02

证据：本次完成源码阅读和摘录核验；未运行这个项目的模型、工具或服务。



排除：远程 sandbox 的隔离强度；Hub / MCP 实际服务；模型基准分数；任意 Python 的安全证明

### 本案例阅读任务

追踪模型文本如何成为代码动作、执行观察和下一轮输入，解释失败步骤如何消耗预算。

读前准备：第 1、3、8 章；能阅读 Python 代码和异常。ActionStep 是内部行动轨迹，尚需转换成模型消息。

1. 先读步骤生命周期，再区分解析失败与执行失败。
2. 追代码、执行日志和 to_messages 的输入投影。
3. 对照导入允许列表和预算耗尽后的兜底答案，记录各自边界。

检验理解：步骤耗尽后仍产生答案，为什么不能据此将样本全部计为 solved？

判断标准：保留 AgentMaxStepsError 与动作轨迹，单独评价答案；解释器限制也不能直接证明操作系统隔离。

阅读主线：MultiStepAgent 驱动有限步循环 → CodeAgent 将输出解析为代码 → Python executor 执行代码并返回日志与结果 → ActionStep 转成后续消息 → 最终答案或预算耗尽结束运行

### 一个行动步骤的生命周期

循环的步骤对象既记录正常观察，也记录失败。AgentGenerationError 被视为实现层错误并重新抛出；其他 AgentError 会进入 action_step.error，随后 finalize、append 和计数仍执行。区分异常类别，可以解释为什么同样显示“错误”，某些运行继续，某些运行停止。

失败步骤也消耗预算，解析错误不会带来额外的免费重试。finally 中的收尾保留失败步骤，便于从轨迹定位故障；内存列表的 append 仍不能证明跨进程持久化。

阅读时不要只追成功返回值；同时记下错误对象、步骤编号、回调和观察消息。错误若没有进入下一轮模型可见输入，Agent 可能重复相同尝试。

源码观察：AgentError 会记入 ActionStep，finally 仍完成步骤、保存并增加计数。

`src/smolagents/agents.py:590-612`

```
                            self._validate_final_answer(final_answer)
                        returned_final_answer = True
                        action_step.is_final_answer = True

            except AgentGenerationError as e:
                # Agent generation errors are not caused by a Model error but an implementation error: so we should raise them and exit.
                raise e
            except AgentError as e:
                # Other AgentError types are caused by the Model, so we should log them and iterate.
                action_step.error = e
            finally:
                self._finalize_step(action_step)
                self.memory.steps.append(action_step)
                yield action_step
                self.step_number += 1

        if not returned_final_answer and self.step_number == max_steps + 1:
            final_answer = self._handle_max_steps_reached(task)
            yield action_step
        final_answer_step = FinalAnswerStep(handle_agent_output_types(final_answer))
        self._finalize_step(final_answer_step)
        yield final_answer_step

```

预测：一次模型动作解析失败，会不会不计入步骤？

参考：符合被捕获 AgentError 的失败仍在 finally 中完成并增加步骤计数。不可把这种重试当成零成本。

### 文本到可执行代码的边界

代码动作可以表达循环、变量和多工具组合，减少把每个小计算都交回模型的需要。代价是动作语言更有表达力：解析、执行资源和能力控制都必须有清楚的边界。这里先提取代码并修正 final_answer 形式，再把代码装入一个 python_interpreter 工具调用记录。

解析错误成为 AgentParsingError。它发生在代码执行之前，因此“产生了动作文本”不能证明工具已运行。定位问题时保存原始输出、解析后代码和执行日志三个版本，避免把模型文本当成实际执行记录。

不要把 CodeAgent 理解为专门帮程序员写项目代码的产品。它可以用代码完成数据查询或数学任务；关键差异是 Agent 的动作表示方式。

源码观察：CodeAgent 解析代码，建立 python_interpreter ToolCall 后再执行。

`src/smolagents/agents.py:1708-1732`

```
                code_action = parse_code_blobs(output_text, self.code_block_tags)
            code_action = fix_final_answer_code(code_action)
            memory_step.code_action = code_action
        except Exception as e:
            error_msg = f"Error in code parsing:\n{e}\nMake sure to provide correct code blobs."
            raise AgentParsingError(error_msg, self.logger)

        tool_call = ToolCall(
            name="python_interpreter",
            arguments=code_action,
            id=f"call_{len(self.memory.steps)}",
        )
        yield tool_call
        memory_step.tool_calls = [tool_call]

        ### Execute action ###
        self.logger.log_code(title="Executing parsed code:", content=code_action, level=LogLevel.INFO)
        try:
            code_output = self.python_executor(code_action)
            execution_outputs_console = []
            if len(code_output.logs) > 0:
                execution_outputs_console += [
                    Text("Execution logs:", style="bold"),
                    Text(code_output.logs),
                ]
```

预测：模型输出了代码块，可以直接把它计为一次成功执行吗？

参考：不可以。还要区分解析成功、executor 被调用、执行成功以及结果符合任务条件。

### 动作输出和日志各有用途

Executor 的输出与运行日志回答不同问题。输出承载计算值；日志帮助解释执行过程。程序调用 self.python_executor(code_action)，再将 logs 组装成观察文本。观察进入下一轮后，模型才有机会根据真正执行的结果调整动作。

日志既可能很长，也可能包含外部内容。保存与展示日志应有长度和敏感信息边界；让模型读到一个网页或工具返回的文本，不应赋予该文本改变运行策略的权限。本书的这个建议来自信任边界推理，不是本摘录已经实现全部防护的承诺。

若执行器返回部分日志后异常，阅读后面的 except 分支才能判断这些信息是否被保留。不要只从返回值类型猜测失败时的观察。

源码观察：Python executor 返回输出与日志；日志被构造成 observation。

`src/smolagents/agents.py:1724-1733`

```
        self.logger.log_code(title="Executing parsed code:", content=code_action, level=LogLevel.INFO)
        try:
            code_output = self.python_executor(code_action)
            execution_outputs_console = []
            if len(code_output.logs) > 0:
                execution_outputs_console += [
                    Text("Execution logs:", style="bold"),
                    Text(code_output.logs),
                ]
            observation = "Execution logs:\n" + code_output.logs
```

预测：动作返回 42，日志写着 retry，应该把哪一个当作最终答案？

参考：两者都只是执行证据；最终答案还需要动作的终止标志及任务验收。

### 轨迹怎样转回模型输入

ActionStep 是内部轨迹结构，模型接收的是消息。to_messages 把 observation 变成工具响应，错误则追加错误说明和“不要重复错误”的提示。这里存在明确的投影步骤：存储了什么与模型看到什么，不必完全相同。

这也是看 summary_mode 等参数时应该保留的心智模型。压缩模式可能减少某些模型输出，但仍需保留决定后续动作的证据。把所有历史对象直接塞进输入，会忽略格式、角色和上下文预算。

本摘录中的错误文字是一种指导，不是重试算法。模型是否改变策略仍是实际运行问题，应通过固定失败样例比较，而不是从提示措辞推导成功率。

源码观察：观察和错误会转换为 TOOL_RESPONSE 消息，错误包含重试提示。

`src/smolagents/memory.py:126-151`

```
        if self.observations is not None:
            messages.append(
                ChatMessage(
                    role=MessageRole.TOOL_RESPONSE,
                    content=[
                        {
                            "type": "text",
                            "text": f"Observation:\n{self.observations}",
                        }
                    ],
                )
            )
        if self.error is not None:
            error_message = (
                "Error:\n"
                + str(self.error)
                + "\nNow let's retry: take care not to repeat previous errors! If you have retried several times, try a completely different approach.\n"
            )
            message_content = f"Call id: {self.tool_calls[0].id}\n" if self.tool_calls else ""
            message_content += error_message
            messages.append(
                ChatMessage(role=MessageRole.TOOL_RESPONSE, content=[{"type": "text", "text": message_content}])
            )

        return messages

```

预测：内存里有错误记录，为什么下一轮可能仍重复原动作？

参考：先查记录是否正确投影为消息、模型实际收到的输入；提示存在也不保证模型遵守。

### 解释器限制与系统隔离

这里逐段检查模块路径的授权树。授权某个导入是开放一种 Python 能力；它不等于操作系统级进程、网络和文件隔离。把解释器允许列表称为“绝对安全沙箱”，会跳过宿主能力和外部工具的风险。

放宽一个模块路径要问具体用途。例如允许网络库可能改变数据外发边界，允许文件库可能改变宿主读取范围。带星号的路径扩大允许范围，审查时应写明它覆盖了哪些能力，而不仅是修复一次 ImportError。

本书没有运行容器或远端执行器，也不比较其安全性。要开展隔离实验，应固定镜像、挂载、网络、资源限制及攻击样例，再把解释器限制与系统边界分开评分。

源码观察：授权导入按模块路径树匹配，星号允许后续路径。

`src/smolagents/local_python_executor.py:372-380`

```
def check_import_authorized(import_to_check: str, authorized_imports: list[str]) -> bool:
    current_node = build_import_tree(authorized_imports)
    for part in import_to_check.split("."):
        if "*" in current_node:
            return True
        if part not in current_node:
            return False
        current_node = current_node[part]
    return True
```

预测：新增 authorized_imports 能证明代码无法访问宿主文件吗？

参考：不能。导入检查与系统隔离是不同边界；还需检查 executor、工具和宿主配置。

### 预算耗尽后的答案不是成功证书

没有最终答案且步骤耗尽时，程序调用 _handle_max_steps_reached。这个辅助函数仍可能生成文本答案，同时把 AgentMaxStepsError 写入步骤。检查结果时，要分别说明是否产出了答案，以及任务是否按动作轨迹完成。

产品应将超限状态和兜底解释一起展示；评测应分别记录终止原因与正确性，不能把生成 FinalAnswerStep 的所有样例都算 solved。一个诚实的“我没完成，以下是已知信息”可能是合适体验，但它不是成功完成工具任务。

迁移练习：构造三个总是报错的动作，预算设为两步，预测错误记录和终态。这个练习可以用独立模型检验计数，但若要证明框架实际行为，仍必须执行该固定版本。

源码观察：达到最大步骤后会调用兜底答案生成，并保存 AgentMaxStepsError。

`src/smolagents/agents.py:605-637`

```

        if not returned_final_answer and self.step_number == max_steps + 1:
            final_answer = self._handle_max_steps_reached(task)
            yield action_step
        final_answer_step = FinalAnswerStep(handle_agent_output_types(final_answer))
        self._finalize_step(final_answer_step)
        yield final_answer_step

    def _validate_final_answer(self, final_answer: Any):
        for check_function in self.final_answer_checks:
            try:
                assert check_function(final_answer, self.memory, agent=self)
            except Exception as e:
                raise AgentError(f"Check {check_function.__name__} failed with error: {e}", self.logger)

    def _finalize_step(self, memory_step: ActionStep | PlanningStep | FinalAnswerStep):
        if not isinstance(memory_step, FinalAnswerStep):
            memory_step.timing.end_time = time.time()
        self.step_callbacks.callback(memory_step, agent=self)

    def _handle_max_steps_reached(self, task: str) -> Any:
        action_step_start_time = time.time()
        final_answer = self.provide_final_answer(task)
        final_memory_step = ActionStep(
            step_number=self.step_number,
            error=AgentMaxStepsError("Reached max steps.", self.logger),
            timing=Timing(start_time=action_step_start_time, end_time=time.time()),
            token_usage=final_answer.token_usage,
        )
        final_memory_step.action_output = final_answer.content
        self._finalize_step(final_memory_step)
        self.memory.steps.append(final_memory_step)
        return final_answer.content
```

预测：出现 FinalAnswerStep 就可以把样例记为 solved 吗？

参考：不可以。需要同时检查超限错误、外部任务完成条件和输出正确性。

### 闭卷复述与迁移

步骤耗尽后仍产生答案，为什么不能据此将样本全部计为 solved？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## Letta Code · 记忆的作用域与投影

长期记忆存在哪里，哪些部分进入上下文，谁有权修改？

来源：https://github.com/letta-ai/letta-code

提交：`1fcc9666817ab852bc2532a3a989f712e1fd6c19`；访问：2026-10-02

证据：本次完成源码阅读和摘录核验；未运行这个项目的模型、工具或服务。



排除：旧 archive 分支的 Python V1 服务；Cloud 同步服务；完整上下文编译器；反思模型的学习效果；跨机器一致性

### 本案例阅读任务

按 Agent 身份、目录格式、投影条件和写入检查理解长期记忆，找出结果被接受的提交边界。

读前准备：第 2、5、8 章；能阅读 TypeScript 分支，知道目录和符号链接。

1. 先核对迁移说明，确认本案例使用的仓库和固定提交。
2. 按显式 Agent、运行上下文与环境回退解析作用域，再检查 v1/v2 布局。
3. 预测嵌套路径的投影结果，最后追写入目标与反思提交检查。

检验理解：记忆文件存在且满足投影路径条件，能证明它已进入模型请求吗？

判断标准：不能。还需检查完整编译与最终请求；本案例只覆盖投影判断和选定写入/提交边界。

阅读主线：先确定当前 agent 与 backend 的作用域 → 解析记忆格式和文件目录 → 按格式选择投影路径 → 写入许可检查原始路径及真实路径 → 反思结果以提交状态决定是否进入父记忆

### 从旧仓库迁移到当前实现

先确认源码位置。冻结快照中的 letta-ai/letta README 将 V1 服务放到 archive，并把活跃实现指向 letta-code。因此本案例采用当前 TypeScript harness；旧文章中的 Python memory block 调用栈需要重新核对，不能直接移用。

本案例因此缩小为“记忆目录、投影和写入边界”。这些具体函数能回答记忆如何组织与保护；它们不能单独证明 Agent 随时间变聪明。学习效果需要真实跨任务样例、冻结评测和反证。

阅读版本固定在本章提交，而不是声称覆盖以后所有版本。更新教材时先查迁移说明和文件变化，再改受影响的概念。

源码观察：当前案例阅读 letta-code，覆盖有状态 Agent 的当前源码；旧 letta 仓库已指向这里。

`README.md:1-18`

```
# Letta Code

[![npm](https://img.shields.io/npm/v/@letta-ai/letta-code.svg?style=flat-square)](https://www.npmjs.com/package/@letta-ai/letta-code) [![Discord](https://img.shields.io/badge/discord-join-blue?style=flat-square&logo=discord)](https://discord.gg/letta)

Letta Code is a stateful agent harness for creating agents that are more like people than tools. Letta Code agents have memory, identity, and a sense of experience over time. They learn and evolve over long horizons through rewriting their own memory, skills, prompts, and even the harness itself (through mods). 

Letta Code can be used interactively, or to power always-on agents that work proactively. Interact with agents through:
* A local [**CLI**](https://docs.letta.com/letta-code/cli)
* The [**desktop app**](https://docs.letta.com/letta-code/desktop-app) for macOS, Windows, and Linux
* Your browser, including [mobile](https://docs.letta.com/letta-code/remote-mobile), at [chat.letta.com](https://chat.letta.com)
* Messaging integrations, including [Telegram](https://docs.letta.com/letta-code/channels#telegram-cli), [Slack](https://docs.letta.com/letta-code/channels#slack-cli), [Discord](https://docs.letta.com/letta-code/channels#discord-cli), and [custom channels](https://github.com/letta-ai/letta-code/blob/main/src/channels/README.md)

![](https://github.com/letta-ai/letta-code/blob/main/assets/letta-code-demo.gif)

## Feature Overview

> [!TIP]
> Letta Code agents are designed to be self-configuring. If you want to configure something (e.g. skills, behavior, hooks, permissions), try asking your agent to do it for you.
```

预测：一篇 MemGPT 旧教程能直接作为本章当前实现的调用链吗？

参考：不能。应确认仓库、分支、语言和当前执行入口；这里采用迁移后的 letta-code。

### 先确定属于哪个 Agent

记忆读写前先解析 Agent 身份。注释说明 runtime-first 优先级；具体代码先检查显式 agentId，再读取运行上下文，最后回退到目录或 Agent 环境变量。追多个 Agent 共用进程的场景时，按这些分支核对目标对象。

getScopedMemoryFilesystemRoot 还会根据 local backend 分别选择存储根。一个全局 MEMORY_DIR 字符串不能描述所有运行作用域；日志应保存被解析的 Agent 身份及作用域，但不把本机敏感路径放入对外轨迹。

本摘录证明选择顺序，未证明所有调用者都正确传入作用域，也未证明跨进程隔离。后续测试应故意让显式 Agent、运行上下文和环境变量不一致，检验优先级与错误处理。

源码观察：记忆目录解析优先采用显式 Agent 或运行作用域，再采用环境变量回退。

`src/agent/memory-filesystem.ts:92-131`

```
 * Resolve the active memory directory for the current execution scope.
 *
 * Precedence is intentionally runtime-first:
 * 1. Explicit agent ID (caller-provided scope)
 * 2. In-process runtime/agent context
 * 3. Explicit MEMORY_DIR env fallback
 * 4. AGENT_ID env fallback
 */
export function resolveScopedMemoryDir(
  options: ResolveScopedMemoryDirOptions = {},
): string | null {
  const env = options.env ?? process.env;
  const homeDir = options.homeDir ?? env.HOME ?? env.USERPROFILE ?? homedir();

  const explicitAgentId = options.agentId?.trim();
  if (explicitAgentId) {
    return getScopedMemoryFilesystemRoot(explicitAgentId, { env, homeDir });
  }

  try {
    const scopedAgentId = getCurrentAgentId().trim();
    if (scopedAgentId) {
      return getScopedMemoryFilesystemRoot(scopedAgentId, { env, homeDir });
    }
  } catch {
    // No runtime-scoped agent context; fall back below.
  }

  const directMemoryDir = (env.LETTA_MEMORY_DIR || env.MEMORY_DIR || "").trim();
  if (directMemoryDir) {
    return resolve(directMemoryDir);
  }

  const envAgentId = (env.LETTA_AGENT_ID || env.AGENT_ID || "").trim();
  if (envAgentId) {
    return getScopedMemoryFilesystemRoot(envAgentId, { env, homeDir });
  }

  return null;
}
```

预测：显式 agentId 与 MEMORY_DIR 指向不同对象，哪个优先？

参考：这里显式 agentId 优先，随后按 backend 解析该 Agent 的根目录。

### 文件布局是一种格式契约

长期记忆不是一个没有结构的文本池。detectMemoryFormat 以根 MEMORY.md 的存在选择 v2；isCoreMemoryPath 对 v2 采用根层 Markdown，对 v1 则检查 system/ 前缀。相同文件名放在不同目录，会有不同的核心记忆语义。

这些条件是布局契约，不是内容质量判断。一个文件可以满足路径规则却含有过时事实；也可以是很有价值的参考资料，却不属于核心记忆。应该分别管理“是否加载”“信息是否有效”和“来源是否可信”。

迁移格式时不能只移动文件而不检查投影、编辑许可和上下文预算。旧路径被正确读取，不代表新布局下仍被同样装配。

源码观察：根 MEMORY.md 选择 memfs-v2；核心 Markdown 路径由格式决定。

`src/agent/memory-format.ts:4-20`

```
export type LocalMemoryFormat = "memfs-v1" | "memfs-v2";

export function detectMemoryFormat(
  memoryDir: string,
  _localMemfs: boolean,
): LocalMemoryFormat {
  return existsSync(join(memoryDir, "MEMORY.md")) ? "memfs-v2" : "memfs-v1";
}

export function isCoreMemoryPath(
  relativePath: string,
  format: LocalMemoryFormat,
): boolean {
  const normalized = relativePath.replace(/\\/g, "/");
  if (!normalized.endsWith(".md")) return false;
  if (format === "memfs-v2") return !normalized.includes("/");
  return normalized.startsWith("system/");
```

预测：reference/detail.md 一定属于 v2 核心记忆吗？

参考：不是。v2 核心路径是根层 .md；嵌套参考文件还需要看投影规则及具体编译流程。

### 目录索引决定可投影路径

isProjectedMemoryPath 展示了存储与上下文装配之间的一层选择。v1 直接允许；v2 对 skills 另行处理，对嵌套路径逐级检查目录索引。目录中有文件，不等于模型在本轮收到该文件的全部正文。

给 reference/ 增加 MEMORY.md，可以改变嵌套资料满足投影条件的结果，但索引存在不能代替内容检索，也不能保证 token 预算内全部装入。完整编译器仍是本案例排除范围，所以这里准确的说法是“符合投影路径判断”，不是“已进入实际请求”。

这种目录契约适合做一个闭卷练习：列五个路径，画目录树，按函数预测每个布尔结果。再去真正的请求构造边界核对模型输入，完成从静态预测到运行证据的最后一步。

源码观察：v2 排除 skills，并要求嵌套目录链上存在 MEMORY.md。

`src/agent/memory-format.ts:23-41`

```
export function isProjectedMemoryPath(
  relativePath: string,
  allPaths: ReadonlySet<string>,
  format: LocalMemoryFormat,
): boolean {
  const normalized = relativePath.replace(/\\/g, "/");
  if (format === "memfs-v1") return true;
  if (normalized === "skills" || normalized.startsWith("skills/")) return false;
  if (!normalized.includes("/")) return true;

  const parts = normalized.split("/");
  const directories = parts.slice(0, -1);
  let current = "";
  for (const directory of directories) {
    current = current ? `${current}/${directory}` : directory;
    if (!allPaths.has(`${current}/MEMORY.md`)) return false;
  }
  return true;
}
```

预测：notes/a/b.md 在 v2 中满足投影规则需要哪些目录索引？

参考：需要 notes/MEMORY.md 与 notes/a/MEMORY.md；路径判断通过仍不等于具体请求完整加载正文。

### 路径许可也要检查符号链接

记忆文件可被 Agent 编辑，会带来写入能力。这里先识别允许的文件写工具，再提取全部目标；每个目标都要通过普通路径检查和 canonicalizeRoot 后的真实路径检查。一个 patch 涉及多个文件时，不能只检查第一个目标。

真实路径检查用于防止记忆目录内的符号链接把写入转向其他位置。代码注释同时指出前置的 cross-agent guard 和 MemFS pre-commit 的 read_only 保护；单个函数不是整个权限系统。

本次未执行符号链接、竞争写入或权限旁路测试。源码说明设计边界，实际安全结论还需要操作系统、具体工具和并发条件下的验证。

源码观察：isOwnMemoryWrite 要求每个目标同时处于逻辑根和解析后的真实根。

`src/permissions/memory-write-allowance.ts:32-62`

```
 * roots, both as written and after resolving symlinks (tolerating a
 * not-yet-existing leaf), so a link planted under the checkout cannot route
 * an auto-approved edit elsewhere. The cross-agent guard runs before this and
 * the MemFS pre-commit hook still protects read_only files.
 */
export function isOwnMemoryWrite(
  canonicalTool: string,
  toolArgs: ToolArgs,
  workingDirectory: string,
  agentId?: string,
): boolean {
  if (!MEMORY_FILE_WRITE_TOOLS.has(canonicalTool)) return false;
  const targets = writeTargets(canonicalTool, toolArgs);
  if (targets.length === 0) return false;
  try {
    const { roots } = resolveAllowedMemoryRoots({
      currentAgentId: agentId ?? getCurrentAgentId(),
    });
    const realRoots = roots.map(canonicalizeRoot);
    return targets.every((target) => {
      const resolved = resolveMemoryTargetPath(target, workingDirectory);
      return (
        resolved !== null &&
        isPathWithinRoots(resolved, roots) &&
        isPathWithinRoots(canonicalizeRoot(resolved), realRoots)
      );
    });
  } catch {
    return false;
  }
}
```

预测：patch 同时改自己的记忆与另一个目录，能因第一个目标合法而整体通过吗？

参考：不能。这里使用 targets.every，要求所有目标同时满足逻辑与真实根检查。

### 未提交的反思不会自动进入父记忆

反思任务写出文字和反思结果被主记忆接受，是两个阶段。这个分支先检查提交数、工作区状态和 HEAD；如果仍有未提交变化，执行清理并返回 dirty_uncommitted。它没有因为“有新文件”就把结果并入父记忆。

这个设计强调可审计的提交边界。读者需要继续追 shouldMerge、冲突处理和编译更新，才能完整描述接受流程；本摘录只证明未提交路径的拒绝行为。函数名含 Unlocked，注释要求调用者已经持有 lease，因此不能从这里推导函数自己提供并发锁。

所谓持续学习至少还包括结果筛选、冲突解决、版本回退和任务效果评测。把保存一份反思 Markdown 称为“持续学习已验证”，会跨越这些尚未检查的环节。

源码观察：反思 worktree 有未提交变化时返回 dirty_uncommitted 并清理，标记可重试。

`src/agent/memory-worktree.ts:402-429`

```
  const commitCount = await getCommitCount(worktree);
  const status = await getStatusPorcelain(worktree.worktreeDir);
  const head = await getHead(worktree.worktreeDir);

  if (status.length > 0) {
    await cleanupWorktreeAndBranch(
      worktree.parentMemoryDir,
      worktree.worktreeDir,
      worktree.branchName,
      { force: true },
    );
    debugLog(
      "memfs-git",
      "reflection finalized id=%s status=dirty_uncommitted commitCount=%d cleanedUp=true retryable=true",
      worktree.id,
      commitCount,
    );
    return {
      status: "dirty_uncommitted",
      parentMemoryDir: worktree.parentMemoryDir,
      reflectionWorktreeDir: worktree.worktreeDir,
      reflectionBranch: worktree.branchName,
      commitCount,
      head,
      summary:
        "Reflection memory worktree had uncommitted changes; it was cleaned up so the transcript can be retried.",
    };
  }
```

预测：反思写了三个文件但没有提交，可以报告父记忆已更新吗？

参考：不可以。此路径返回 dirty_uncommitted，清理并保留可重试语义；需要查看实际接受和重编译结果。

### 闭卷复述与迁移

记忆文件存在且满足投影路径条件，能证明它已进入模型请求吗？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## browser-use · 观察过期以后该停在哪里

模型根据页面快照提出一串动作，页面变化后剩余动作还能执行吗？

来源：https://github.com/browser-use/browser-use

提交：`302d8fcb245a7a63fb7531a4734c9ce3c7792779`；访问：2026-10-02

证据：本次完成源码阅读和摘录核验；未运行这个项目的模型、工具或服务。



排除：真实站点任务成功率；Cloud 浏览器与反检测服务；账号 Cookie / 生产鉴权；完整 DOM 序列化器；交易或对外提交

### 本案例阅读任务

从页面观察追到动作批次与终态，解释页面变化后哪些动作必须停止。

读前准备：第 1、3 章；能阅读 Python 异步调用。页面观察是采样后的输入，不等于浏览器的全部状态。

1. 追上一轮结果如何装入上下文，再清理本轮临时状态。
2. 按顺序记录每个动作的结果、URL 和焦点变化。
3. 分别预测旧动作失效、done/success 不一致、暂停和连续失败。

检验理解：URL 未变时，为什么也不能默认执行剩余旧动作？

判断标准：说明焦点和页面内容仍可能变化；现有摘录不证明检测了所有 DOM 变化，真实浏览器路径未运行。

阅读主线：step 收集浏览器状态和截图 → 上下文装配后清理上一轮临时状态 → 模型给出动作列表 → multi_act 逐个调用工具 → 页面变化、错误或 done 截断动作序列 → 重新观察并进入下一步

### 先用旧结果装配，再清理临时状态

浏览器任务里上一轮结果需要进入本轮输入，但不应在本轮超时时冒充新结果。代码因此先 _prepare_context，再把 last_model_output 和 last_result 置空，然后调用模型、执行动作和后处理。顺序就是这个设计的关键。

如果先清空，上一轮工具观察可能丢失；如果不清空，模型调用超时后可能留下旧动作，让后续处理误认为本轮已经生成了新动作。阅读状态更新时，应同时写出“谁先消费旧值”和“谁负责产生新值”。

finally 总会 finalize，本轮失败也可以进入历史。用模型超时和动作异常检查这条路径时，要核对 last_result 来自哪一轮，以及清理与写入的先后关系；页面展示不能替代这些状态证据。

源码观察：step 先准备上下文，再清空 last_model_output 与 last_result，随后执行新动作。

`browser_use/agent/service.py:1064-1091`

```
			browser_state_summary = await self._prepare_context(step_info)

			# Clear previous step state after context preparation (which needs
			# them for the "previous action result" prompt) but before the LLM
			# call, so a timeout during _get_next_action or _execute_actions
			# won't leave stale data from the previous step.
			self.state.last_model_output = None
			self.state.last_result = None

			# Phase 2: Get model output and execute actions
			await self._get_next_action(browser_state_summary)
			await self._execute_actions()

			# Phase 3: Post-processing
			await self._post_process()

		except Exception as e:
			# Handle ALL exceptions in one place
			await self._handle_step_error(e)

		finally:
			await self._finalize(browser_state_summary)

	async def _prepare_context(self, step_info: AgentStepInfo | None = None) -> BrowserStateSummary:
		"""Prepare the context for the step: browser state, action models, page actions"""
		# step_start_time is now set in step() method

		assert self.browser_session is not None, 'BrowserSession is not set up'
```

预测：为什么不能把两处置空移到 _prepare_context 之前？

参考：上下文准备还需要上一轮结果；提前清空会删除本轮提示所需的观察。

### 浏览器观察包含状态与截图

Agent 使用 get_browser_state_summary 的结果、截图和筛选后的动作说明。排查缺失控件时，依次检查浏览器实际状态、序列化观察和最终模型输入，确认信息在哪一层遗漏；本轮观察不包含网站的全部状态。

代码请求截图，即使不以视觉模式调用模型，也可能用于同步或轨迹。截图获取不等于模型收到了截图，更不等于模型正确识别按钮。动作模型还会按页面 URL 更新，这意味着页面变化也可能改变可用动作集合。

遇到点击错误，应保存该动作所依据的观察时间、页面和目标身份，再检查执行时是否还是同一状态。只保存“click index=7”无法充分解释为什么点击了另一个控件。

源码观察：上下文准备获取 browser state summary，包含截图，并按页面更新动作模型。

`browser_use/agent/service.py:1093-1123`

```
		self.logger.debug(f'🌐 Step {self.state.n_steps}: Getting browser state...')
		# Always take screenshots for all steps
		self.logger.debug('📸 Requesting browser state with include_screenshot=True')
		browser_state_summary = await self.browser_session.get_browser_state_summary(
			include_screenshot=True,  # always capture even if use_vision=False so that cloud sync is useful (it's fast now anyway)
			include_recent_events=self.include_recent_events,
		)
		if browser_state_summary.screenshot:
			self.logger.debug(f'📸 Got browser state WITH screenshot, length: {len(browser_state_summary.screenshot)}')
		else:
			self.logger.debug('📸 Got browser state WITHOUT screenshot')

		# Check for new downloads after getting browser state (catches PDF auto-downloads and previous step downloads)
		await self._check_and_update_downloads(f'Step {self.state.n_steps}: after getting browser state')

		self._log_step_context(browser_state_summary)
		await self._check_stop_or_pause()

		# Update action models with page-specific actions
		self.logger.debug(f'📝 Step {self.state.n_steps}: Updating action models...')
		await self._update_action_models_for_page(browser_state_summary.url)

		# Get page-specific filtered actions
		page_filtered_actions = self.tools.registry.get_prompt_description(browser_state_summary.url)

		# Page-specific actions will be included directly in the browser_state message
		self.logger.debug(f'💬 Step {self.state.n_steps}: Creating state messages for context...')

		# Get unavailable skills info if skills service is enabled
		unavailable_skills_info = None
		if self.skill_service is not None:
```

预测：截图已经生成，能证明模型按截图决策了吗？

参考：不能。要继续核对消息装配、模型输入模式及具体动作引用的观察。

### 一串动作按顺序执行

模型可以一次提出多个动作，但 Runtime 不应把它们当成已经完成的一组事实。multi_act 每次调用 tools.act 后追加结果，再看 done、error 和序列位置。第一步成功、第二步失败时，结果应能表达部分成功，避免重试整组造成重复副作用。

这里是顺序执行，不是把同一页面上的动作并发发出去。页面控件与焦点都有状态依赖，后一个动作往往需要前一个动作成功后才有意义。批量提案可以减少模型往返，但必须保留执行边界。

不要从这一截断逻辑推导外部操作幂等。例如提交表单后网络断开，程序未必能确定提交是否发生；仍要检查服务端状态或使用业务幂等机制。

源码观察：multi_act 调用 tools.act，保存部分结果，done 或 error 会截断序列。

`browser_use/agent/service.py:2780-2810`

```
				pre_action_focus = self.browser_session.agent_focus_target_id

				result = await self.tools.act(
					action=action,
					browser_session=self.browser_session,
					file_system=self.file_system,
					page_extraction_llm=self.settings.page_extraction_llm,
					sensitive_data=self.sensitive_data,
					available_file_paths=self.available_file_paths,
					extraction_schema=self.extraction_schema,
				)

				if result.error:
					await self._demo_mode_log(
						f'Action "{action_name}" failed: {result.error}',
						'error',
						{'action': action_name, 'step': self.state.n_steps},
					)
				elif result.is_done:
					completion_text = result.long_term_memory or result.extracted_content or 'Task marked as done.'
					level = 'success' if result.success is not False else 'warning'
					await self._demo_mode_log(
						completion_text,
						level,
						{'action': action_name, 'step': self.state.n_steps},
					)

				results.append(result)

				if results[-1].is_done or results[-1].error or i == total_actions - 1:
					break
```

预测：第二个动作失败，可以说这一批动作完全没有发生吗？

参考：不可以。前面动作可能已经成功，需要根据部分结果和外部状态决定下一步。

### 页面变化会使剩余动作失效

页面观察有有效期。点击导航后，旧的元素索引和动作假设可能不再有效。代码提供两层判断：工具元数据声明 terminates_sequence；运行后 URL 或焦点 target 发生变化。命中任意一层就停止剩余动作，让下一轮重新观察。

URL 未变不代表页面完全未变，比如同页弹窗或异步列表刷新。这个摘录显示已有的检测维度，不能被扩大为“检测到所有 DOM 变化”。还需要阅读其他定位与节点检查，并用固定页面变化测试覆盖遗漏。

跨项目迁移时，可以把“观察版本”作为动作参数的一部分：执行前校验动作依据的对象仍有效。如果过期，重新观察比继续使用旧索引更容易恢复。该建议属于本书推理，未声称这里已实现统一版本戳协议。

源码观察：动作元数据或 URL / focus target 的变化都会让剩余序列停止。

`browser_use/agent/service.py:2812-2828`

```
				# --- Page-change guards (only when more actions remain) ---

				# Layer 1: Static flag — action metadata declares it changes the page
				registered_action = self.tools.registry.registry.actions.get(action_name)
				if registered_action and registered_action.terminates_sequence:
					self.logger.info(
						f'Action "{action_name}" terminates sequence — skipping {total_actions - i - 1} remaining action(s)'
					)
					break

				# Layer 2: Runtime detection — URL or focus target changed
				post_action_url = await self.browser_session.get_current_page_url()
				post_action_focus = self.browser_session.agent_focus_target_id

				if post_action_url != pre_action_url or post_action_focus != pre_action_focus:
					self.logger.info(f'Page changed after "{action_name}" — skipping {total_actions - i - 1} remaining action(s)')
					break
```

预测：动作改变焦点 target 但 URL 不变，剩余动作会继续吗？

参考：本分支比较 URL 或 focus target；焦点 target 变化就会停止。

### done 与 success 的关系

普通动作成功不代表整个任务成功。ActionResult 允许普通步骤留下 success=None；只有声明任务完成时才应该设置整体成功。验证器拒绝 success=True 而 is_done 不为 True 的组合，让不一致状态早点暴露。

还要区分 Agent 自己声明成功和独立验收成功。完成动作可能说“已找到最低价”，但独立检查需要核对查询时间、候选范围和价格来源。Agent 的布尔字段是运行结果的一部分，不是独立裁判。

long_term_memory 是这个结果结构中的观察字段，不能因为名字里有 memory 就等同于跨会话的长期知识库。不同项目的同名词，需要回到生命周期和实际保存位置理解。

源码观察：ActionResult 分开表达结束、成功与错误；success=True 要求 is_done=True。

`browser_use/agent/views.py:307-347`

```
class ActionResult(BaseModel):
	"""Result of executing an action"""

	# For done action
	is_done: bool | None = False
	success: bool | None = None

	# For trace judgement
	judgement: JudgementResult | None = None

	# Error handling - always include in long term memory
	error: str | None = None

	# Files
	attachments: list[str] | None = None  # Files to display in the done message

	# Images (base64 encoded) - separate from text content for efficient handling
	images: list[dict[str, Any]] | None = None  # [{"name": "file.jpg", "data": "base64_string"}]

	# Always include in long term memory
	long_term_memory: str | None = None  # Memory of this action

	# if update_only_read_state is True we add the extracted_content to the agent context only once for the next step
	# if update_only_read_state is False we add the extracted_content to the agent long term memory if no long_term_memory is provided
	extracted_content: str | None = None
	include_extracted_content_only_once: bool = False  # Whether the extracted content should be used to update the read_state

	# Metadata for observability (e.g., click coordinates)
	metadata: dict | None = None

	# Deprecated
	include_in_memory: bool = False  # whether to include in extracted_content inside long_term_memory

	@model_validator(mode='after')
	def validate_success_requires_done(self):
		"""Ensure success=True can only be set when is_done=True"""
		if self.success is True and self.is_done is not True:
			raise ValueError(
				'success=True can only be set when is_done=True. '
				'For regular actions that succeed, leave success as None. '
				'Use success=False only for actions that fail.'
```

预测：一次点击成功是否应填 success=True？

参考：普通动作通常留 success=None；这里 success=True 只允许与任务结束 is_done=True 组合。

### 暂停、停止和失败预算

暂停意味着还有一个等待恢复的运行；停止意味着退出；连续失败则给出明确失败原因。while 循环在每轮边界处理这些状态，然后才调用 _execute_step。用一个 busy 布尔值描述全部过程，会让 UI 和恢复逻辑难以判断该做什么。

这里失败阈值还会受 final_response_after_failure 影响，给最后解释留出机会。解释文字与任务成功仍要分开。max_steps 是本项目自己的步骤口径，不能直接和 Agents SDK 的模型 turn 或 LangGraph 的 superstep 对比。

当前只核验静态路径，没有运行真实网页、浏览器重连或取消竞态。做运行评测时，应固定网页夹具和动作输出，再分别测试暂停恢复、连续失败和页面过期，避免把网络噪音混进状态机结论。

源码观察：主循环区分暂停等待、连续失败终止、主动停止与任务 done。

`browser_use/agent/service.py:2600-2635`

```
			while self.state.n_steps <= max_steps:
				current_step = self.state.n_steps - 1  # Convert to 0-indexed for step_info

				# Use the consolidated pause state management
				if self.state.paused:
					self.logger.debug(f'⏸️ Step {self.state.n_steps}: Agent paused, waiting to resume...')
					await self._external_pause_event.wait()
					signal_handler.reset()

				# Check if we should stop due to too many failures, if final_response_after_failure is True, we try one last time
				if (self.state.consecutive_failures) >= self.settings.max_failures + int(
					self.settings.final_response_after_failure
				):
					self.logger.error(f'❌ Stopping due to {self.settings.max_failures} consecutive failures')
					agent_run_error = f'Stopped due to {self.settings.max_failures} consecutive failures'
					break

				# Check control flags before each step
				if self.state.stopped:
					self.logger.info('🛑 Agent stopped')
					agent_run_error = 'Agent stopped programmatically'
					break

				step_info = AgentStepInfo(step_number=current_step, max_steps=max_steps)
				is_done = await self._execute_step(current_step, max_steps, step_info, on_step_start, on_step_end)

				if is_done:
					# Agent has marked the task as done
					if self._demo_mode_enabled and self.history.history:
						final_result_text = self.history.final_result() or 'Task completed'
						await self._demo_mode_log(f'Final Result: {final_result_text}', 'success', {'tag': 'task'})

					should_delay_close = True
					break
			else:
				agent_run_error = 'Failed to complete task in maximum steps'
```

预测：paused 和 stopped 可以共用一个“运行结束”状态吗？

参考：不合适。paused 在此等待恢复，stopped 退出；二者的下一步动作和资源生命周期不同。

### 闭卷复述与迁移

URL 未变时，为什么也不能默认执行剩余旧动作？

请用路径图和一个新输入说明预测、源码依据及未验证条件。

## 后续候选与边界

### τ²-bench · 优先补入

工具—Agent—用户的交互评测。与 Inspect 的通用任务框架互补，能把领域约束和最终环境状态纳入研究。

下一次拆解：追一个用户模拟器、Agent 动作、环境状态与 scorer 的完整样例；冻结数据与策略。

https://github.com/sierra-research/tau2-bench

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### OpenSandbox · 优先补入

执行基础设施与隔离边界。补充现有书中尚未实测的沙箱、命令执行和资源生命周期。

下一次拆解：先固定一个受限运行环境，验证创建、执行、超时、清理和挂载/网络边界。

https://github.com/opensandbox-group/OpenSandbox

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### Pydantic AI · 优先补入

类型驱动的输入输出与重试。与 Eino 的 Go 类型接口对照，研究 Python 类型如何进入验证和动作循环。

下一次拆解：追结构化输出无效→验证错误→重试输入；分清类型检查与业务真实性。

https://github.com/pydantic/pydantic-ai

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### Google ADK · 下一批

Agent / workflow / session / evaluation。官方 README 已为 ADK 2.0，值得与 LangGraph 和 Agents SDK 对照控制与会话边界。

下一次拆解：固定 2.0 提交，先追一个最小 Agent 和一个显式 workflow；不沿用旧版本教程调用链。

https://github.com/google/adk-python

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### Microsoft Agent Framework · 下一批

Python 与 .NET 的编排契约。AutoGen 官方把新项目指向这里，适合研究迁移和跨运行时接口。

下一次拆解：选定一种语言，追会话、工具与一个 workflow；另开迁移对照表，避免混合旧 API。

https://github.com/microsoft/agent-framework

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### Mastra · 下一批

TypeScript workflow 与 suspend / resume。补充应用端 workflow、存储与上下文装配，方便与 Pi 的会话状态比较。

下一次拆解：追一次 suspend→持久状态→resume；先核对目录许可，README 描述 Apache 核心与 ee/ 企业条款。

https://github.com/mastra-ai/mastra

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### AgentScope · 专题候选

可观测的多 Agent 编排。可对照消息、工具、记忆和角色协作；需要用明确差异筛选，避免重复已有调度案例。

下一次拆解：选一个多参与者任务，记录消息路由、失败传播和 budget；不先扩展为全部产品拆解。

https://github.com/agentscope-ai/agentscope

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### Mem0 · 专题候选

记忆层的抽取、更新与检索。可以与 Letta 的有状态 harness 对照，检验独立 memory layer 的责任。

下一次拆解：冻结 add / update / delete / search 的输入，测试纠正、重复、用户隔离和时效。

https://github.com/mem0ai/mem0

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### CrewAI · 专题候选

角色任务与事件驱动 Flow。可以比较 Crew 的角色分工和 Flow 的显式控制；研究价值取决于具体失败契约。

下一次拆解：选择一个 Flow 与一个 Crew，比较状态保存、委派和终止责任；分清开源与托管产品说明。

https://github.com/crewAIInc/crewAI

当前仅核对官方 README 与元数据；未计入已完成源码案例。

### AutoGen · 历史对照

分层架构与迁移。当前 README 明确维护模式；适合研究设计演化，新增实现优先读继任 Agent Framework。

下一次拆解：固定旧版本研究 Core / AgentChat / Extensions 的分层，再对照官方迁移指南。

https://github.com/microsoft/autogen

当前仅核对官方 README 与元数据；未计入已完成源码案例。
