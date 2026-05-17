# Stock Trading Strategist Skill (股票交易策略导师)

这是一个基于 [Agent Skills 规范](https://agentskills.io) 构建的自定义 AI 技能。它的核心目标并不是预测明日的股票涨跌，而是作为一位**极其严格、冷静、绝对遵守纪律的“交易导师”**，在您准备开仓（买入）或平仓（卖出）时，对您的交易计划进行全方位的灵魂拷问和逻辑审查。

## 🌟 核心能力 (Features)

本技能融合了多部中外经典交易著作的系统化智慧，能够精准识别并纠正散户在交易中常见的致命错误：
* **海龟交易系统集成**：引入完整的海龟系统执行法则（`references/turtle_complete_rules.md`）与基于ATR（N值）的仓位计算和资金管理法则（`references/turtle_position_sizing.md`）。提供波动率标准化仓位管理、2N止损与1/2N加仓间距等硬性量化规则。
* **大作手利弗莫尔的真实智慧**：严格依据《股票大作手回忆录》原书更新（`references/livermore_wisdom.md`），引入“最小阻力线”、时机确认、“赚大钱靠坐得住”、盈利基础上的金字塔式金字塔加仓等绝对纪律，彻底击碎抄底接飞刀、向下摊薄成本的幻觉。
* **深度交易心理与逆本能训练**：整合布雷特·斯蒂恩博格《投资交易心理分析》（`references/wisdom/03_psychology.md`），提供“激活内部观察员”、“过度自信为反向指标”及“逆本能控制对照表”等具体实战心理自诊工具，将情绪转化为可量化的反向线索。
* **风控与止损底线**：无条件审查计划中是否包含明确的止损点与合理的资金仓位管理。
* **微观临界点甄别**：利用趋势前提法则，甄别 K 线形态的真伪，防止将高位“上吊线”错认为底部“锤子线”（提取自《日本蜡烛图技术新解》）。
* **A股本土实战风控**：强调 20日均线生命线、量价配合，严禁在情绪亢奋的早盘盲目追高，严禁左侧猜底接飞刀（提取自多部A股实战手记）。

## 📁 目录结构 (Structure)

```text
.
├── SKILL.md             # 技能主指令文件，定义了导师的审查 Checklist 和执行流程
├── references/          # 核心知识库 (Agent 在评估计划前必须读取)
│   ├── chip_distribution_analysis.md      # 筹码分布与主力行为识别
│   ├── classic_trend_analysis.md           # [NEW] 股市趋势技术分析 (经典形态、3%突破过滤器、测算目标)
│   ├── japanese_candlestick_techniques.md  # K 线反转形态与趋势法则
│   ├── livermore_wisdom.md                 # 杰西·利弗莫尔大局观与纪律（基于原著16大智慧扩充）
│   ├── practical_a_share_trading.md        # A股实战原则 (均线、量价、T+1风控)
│   ├── ruler_rule_trend_channel.md         # 直尺法则与趋势通道
│   ├── stock_trading_practice_tw.md        # 股票操作学 (量价关系、缺口理论、颈线)
│   ├── turtle_complete_rules.md            # [NEW] 海龟系统执行全规则 (20/55突破、快变市场、建仓出场)
│   ├── turtle_position_sizing.md          # [NEW] 海龟仓位管理与风控 (ATR N值计算、波动性标准化)
│   ├── wisdom_of_trading_rules.md          # 基础生存法则 (止损、资金管理)
│   ├── yang_millionaire_tactics.md         # 逃顶抄底策略与牛熊周期轮回
│   └── wisdom/                             # [NEW] 核心炒股智慧四合一模块
│       ├── 01_core_principles.md           # 基础生存与纪律法则
│       ├── 02_technical_rules.md           # 技术系统设计与量价配合
│       ├── 03_psychology.md                # 交易心理障碍与心理训练（含斯蒂恩博格进阶工具）
│       └── 04_masters_and_bubbles.md       # 大师智慧精髓与泡沫应对
├── scripts/             # 自动化工具脚本
│   └── analyze_trend.py # 获取近期股价、均线及短期趋势的 Python 脚本
└── README.md            # 项目说明文档
```

## 🛠️ 前置要求 (Prerequisites)

为了让 Agent 能够自动调用 `analyze_trend.py` 获取股票的客观数据（以甄别用户所描述的“趋势”是否属实），您的本地环境需要安装以下 Python 库：
```bash
pip3 install akshare pandas
```

## 🚀 如何使用 (How to Use)

当您在与 Claude/Agent 交互时，只需用自然语言描述您的交易计划。例如：

> *"我想买入贵州茅台（600519），目前价格大概跌了很多了，我觉得是底部了。我准备先拿 50% 仓位买入，如果再跌我就补仓，把成本降下来。止损暂且不设，毕竟是好公司，我不信它能跌没。"*

系统将自动触发该 Skill，导师 Agent 会读取知识库并严厉地拆解您的计划，指出其中的“接飞刀”、“不止损”、“向下摊薄”等自杀式行为，并最终给出 **💰 批准**, **🟡 警告**, 或 **❌ 否决** 的客观建议。

