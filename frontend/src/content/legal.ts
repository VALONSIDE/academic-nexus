import { APP_VERSION } from '@/version'

export type LegalDocumentId =
  | 'terms'
  | 'privacy'
  | 'ai'
  | 'subscription'
  | 'content'
  | 'security'
  | 'minors'
  | 'storage'
  | 'rights'

type Section = [title: string, ...paragraphs: string[]]

export interface LegalDocument {
  id: LegalDocumentId
  title: string
  eyebrow: string
  summary: string
  sections: Section[]
  links?: { label: string; href: string }[]
}

export const LEGAL_UPDATED_AT = '2026-11-19'
export const PROJECT_REPOSITORY = 'https://github.com/VALONSIDE/academic-nexus'

const copyrightRule = 'https://ipc.court.gov.cn/zh-cn/news/view-6245.html'
const privacyLaw = 'https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_f374e8245320413181742e6d1baf4366.html'
const aiLabelRule = 'https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm'

function documentSet(label: string, documents: Omit<LegalDocument, 'eyebrow'>[]): LegalDocument[] {
  return documents.map(item => ({ ...item, eyebrow: `${APP_VERSION} · ${label} ${LEGAL_UPDATED_AT}` }))
}

export const legalDocuments = {
  'zh-CN': documentSet('更新于', [
    {
      id: 'terms',
      title: '智导未来服务协议',
      summary: '适用于合作院校授权的账户以及学术画像、师生匹配、资源、订阅和 AI 学术助手。',
      sections: [
        ['服务与协议主体', '智导未来（AcademicNexus）由各部署的服务运营方为合作院校提供。具体运营方、涉及个人信息的责任主体和联络方式由该部署的正式公告载明。自行部署者应为自己的服务和数据处理提供相应告知。激活时请分别阅读并确认本协议和隐私政策。'],
        ['账户、工作台和权限', '师生凭预注册回执中的 Access Key 激活账户。请提供真实资料并妥善保管密码和凭证。兼任管理员的师生使用同一账号切换工作台，各项操作受对应角色及院校权限约束。不得共享账户、冒用身份、绕过授权或配额。'],
        ['院校服务与使用规范', '尊重适用法律、院校规则、知识产权和学术诚信。不得滥用托管服务实施未经授权的数据采集、骚扰、欺诈、侵害隐私或干扰系统。师生双选以系统记录的状态和院校制度为准。匹配分数、通知和 AI 建议供人工判断使用。'],
        ['运营调整、权利与协议更新', '为维护服务、安全或履行法定义务，运营方可在必要范围内调整服务、记录事件或限制违规账户，并通过适用渠道告知。涉及用户权益的实质性条款变更会适当告知，并在适用法律要求时另行取得同意。强制性法定权利和责任依适用法律执行。'],
      ],
    },
    {
      id: 'privacy',
      title: '隐私政策',
      summary: '说明身份和联系方式如何使用、哪些数据可能交由外部服务处理，以及个人信息权利的请求方式。',
      sections: [
        ['责任主体与联系方式', '个人信息处理者、联系方式、部署地域及院校和运营方各自承担的处理职责，以实际部署公示为准。涉及个人信息的请求可通过所属院校管理员转交该部署的责任主体。'],
        ['收集来源、目的和范围', '院校提供姓名、学工号、校院信息和预注册角色。激活时处理账号、Access Key 校验信息、密码哈希及服务协议和隐私政策的确认时间。师生完成设置时需提供邮箱和微信号，手机号可选。平台还按实际使用处理学术画像、资源、双选状态、订阅及额度、通知、AI 对话和必要的安全操作记录，用于提供相应功能、维护安全和履行适用义务。'],
        ['站内查看与联系', '邮箱、手机号和微信号默认隐藏，可逐项选择是否向同校用户展示。院校管理员仅在授权院校范围内查看已公开的联系字段；超级管理员可按账户管理职责查看和更正普通师生的联系方式。管理员账户不提供联系方式编辑功能，个人联系方式也不会通过师生联系功能展示。发邮件时会打开本机邮件程序，复制联系信息会写入设备剪贴板。实际发送及其记录按相关客户端和服务规则处理。'],
        ['外部模型、推荐和数据提供', '使用 AI 学术助手时，请求、近期会话和该场景所需的画像、资源或候选上下文可能发送给所选且已配置的模型服务商，例如 DeepSeek、MiniMax、OpenAI 或通义千问。主动选择同校对象起草消息时，该渠道已公开的联系信息会供本次请求使用。启用语义排序时，经筛选的学术文本可能交由硅基流动处理。部署方应公示实际接收方、处理目的、方式、数据类别、保存安排和适用地域。依法需要单独同意、影响评估或跨境程序时，应在处理前完成。'],
        ['保存、安全与你的权利', '账户、资源、会话和业务记录按处理目的、部署方公示期限及法定义务保存。你可以修改可编辑资料和展示设置，也可删除自己的 AI 会话。删除平台内会话不直接删除第三方依法或依其条款留存的数据。查阅、复制、更正、删除、撤回同意、注销及投诉等请求见用户权利与争议处理规则。'],
      ],
      links: [{ label: '《中华人民共和国个人信息保护法》', href: privacyLaw }],
    },
    {
      id: 'ai',
      title: 'AI 服务与算法辅助说明',
      summary: '说明外部模型、匹配建议、生成内容标识和双选办理卡片。',
      sections: [
        ['模型和输入范围', '根据部署配置选择可用模型。平台会发送完成当前任务所需的对话和上下文。请勿提交密码、Key、未授权的他人资料或与任务无关的敏感信息。起草邮件、短信或微信消息时，平台按站内展示设置校验选定联系人。草稿由你核对并在相应客户端发送。'],
        ['输出核验与标识', '聊天中的模型回复标有“AI 生成”。回答可能出现事实、来源、推理或引用错误。对外复制、发布或提交时，按适用规定及院校要求保留、补充 AI 标识并披露使用情况，核对事实、出处、个人信息及授权。'],
        ['匹配排序与双选操作', '匹配排序依据画像中的学术信息提供相关性建议。你可以修正画像、按条件筛选候选并自主决定是否发起双选。服务端按学校、角色和双选状态生成办理卡片，点击办理按钮才会提交操作，并再次校验权限和额度。录取、评价及其他重要决定由有权人员依适用规则作出。'],
        ['反馈', '对推荐结果、涉嫌侵权内容、偏见、错误或安全问题，请记录发生时间和必要定位信息，通过所属院校管理员反馈。提交反馈时请遮蔽无关信息。'],
      ],
      links: [{ label: '《人工智能生成合成内容标识办法》', href: aiLabelRule }],
    },
    {
      id: 'subscription',
      title: '订阅服务规则',
      summary: '说明普通与高级订阅、额度扣减、院校库存、Key 和交付。',
      sections: [
        ['档位与周期', '普通、Pro、Ultra、Max 每周期初始 AI 额度分别为 10、50、100 和 200 点。轻量和标准模式每次成功请求消耗 1 点，专家模式消耗 2 点。普通周期以注册日开始，高级周期以激活日开始。高级周期结束后回到普通订阅，以账户页显示的档位、余额和周期为准。'],
        ['分配、签发和回收', '超级管理员向院校分配可签发库存，并可向目标院校的在任管理员发送定向提醒。授权院校管理员可在本校范围内签发和交付 Key，并接收系统通知及超级管理员提醒。Key 一次性有效并绑定院校，有效高级周期内不可叠加激活。未激活 Key 可依法依规回收并返还库存，已激活 Key 不可通过回收功能撤销。'],
        ['交付方式', '签发时下载 Excel 订阅回执。在交付页导入后可校验 Key、为合格的指定账户直接激活，或导出指定对象或通用 PDF。直接激活会消耗 Key，导出 PDF 保留 Key 原状态。通用 PDF 未指定账户，仅可按院校规则交付使用。'],
        ['费用和核查', '本版本通过院校分配权益，不在站内向个人提供在线支付、代扣或自动续费。请通过所在院校核对交付、额度及异常扣减，避免交易或公开转发 Key。'],
      ],
    },
    {
      id: 'content',
      title: '著作权、源码与内容规范',
      summary: '说明公开仓库的许可状态、平台与第三方作品的权利，以及师生内容的使用范围。',
      sections: [
        ['项目源码与著作权', '智导未来（AcademicNexus）的 GitHub 仓库公开可见，项目目前未采用开源许可证。著作权等依法享有的权利由相应权利人保留。查看和在 GitHub 上派生仓库适用 GitHub 服务条款。复制、修改、再分发、部署运营或商业使用，应依适用法律或取得相应权利人的授权。平台使用资格依据服务协议或院校授权确定。'],
        ['第三方组件和项目标识', '第三方库、字体、图标及素材适用其各自的许可证、署名或其他权利声明。项目声明仅及于相应权利人对项目原创部分所享有的权利。使用项目名称、图形标识或院校标识仍应遵守相应权利和授权条件。'],
        ['用户内容与资源', '你对有权提交的原创内容保留相应权利。上传资源或填写画像前应确认授权范围。你允许当前部署在提供你使用的功能所需范围内存储、处理并向可见范围内的用户展示这些内容。请勿将受限制的论文、课程材料或他人资料对外传播。'],
        ['AI 输出与投诉', '使用生成内容前应核对出处、受保护表达、第三方权利及学术诚信要求。侵权投诉请提供内容位置、权利主张和必要证明，可通过所属院校的联络渠道提交。'],
      ],
      links: [
        { label: '项目 GitHub 仓库', href: PROJECT_REPOSITORY },
        { label: '《计算机软件保护条例》', href: copyrightRule },
      ],
    },
    {
      id: 'security',
      title: '信息安全与 Key 保护说明',
      summary: '保护登录凭证、激活回执、订阅回执和离线文件。',
      sections: [
        ['账户和安全记录', '密码以哈希校验。会话有有效期，密码变更、管理员重置或账户停用会使旧会话失效。平台使用角色与院校范围校验、请求限制和必要的管理员操作审计。请使用独立密码，共享设备使用后请退出。'],
        ['激活回执和订阅 Key', 'Access Key 与订阅 Key 使用哈希和指纹校验。待激活账户丢失回执时，超级管理员可重新签发 Excel 回执，旧 Access Key 及未完成注册的旧会话随之失效。订阅 Key 的 Excel 回执在签发时提供，导入后用于校验和交付。'],
        ['离线文件与事件报告', '回执及 PDF 可能含个人信息或可兑换凭证。只向授权接收者分发，在受控位置保存，按需要及时清理。发生遗失、误发或疑似未授权访问时，请及时联系所属院校管理员。院校和运营方应采取适用的核验、控制、通报和保护措施。'],
      ],
    },
    {
      id: 'minors',
      title: '未成年人保护声明',
      summary: '面向授权院校说明未成年用户的信息保护和监护人请求渠道。',
      sections: [
        ['开通与监护', '院校向未成年人开通服务前，应按年龄、使用场景和适用法律建立保障措施。处理不满十四周岁未成年人的个人信息应取得其父母或者其他监护人的同意，并制定专门处理规则。相关告知与验证由实际部署方提供。'],
        ['资料与 AI 使用', '院校人员、监护人和用户应限制未成年人资料的收集、展示和共享。请勿在资源或外部 AI 请求中提交不必要的身份、联系方式及其他敏感资料。发现伤害、骚扰或不当传播时，请通过所属院校的联络渠道报告。'],
        ['监护人请求', '监护人可以向实际部署公示的责任主体或通过所属院校提出查阅、更正、删除、限制处理或撤回同意等请求。受理方会核验身份和监护关系，避免向无权人员披露资料。'],
      ],
      links: [{ label: '《中华人民共和国个人信息保护法》', href: privacyLaw }],
    },
    {
      id: 'storage',
      title: '本地存储与登录状态说明',
      summary: '列出浏览器保存的信息及清除方式。',
      sections: [
        ['本地和会话存储', '浏览器本地存储保存访问令牌、账户资料副本、语言和所选 AI 服务商偏好。包括账户资料中返回的本人联系字段。注册临时令牌和角色存放在会话存储中。离线交付页的订阅 Key 存放于该页面的运行内存，下载的 Excel 与 PDF 则由浏览器或设备保存。'],
        ['清理和客户端控制', '退出登录清除应用保存的登录和临时注册状态。语言与 AI 服务商偏好可通过清除站点数据去除。设备上的下载文件、剪贴板和本机邮件草稿需要在对应设备或客户端管理。清除浏览器数据不会清除服务端业务记录。'],
      ],
    },
    {
      id: 'rights',
      title: '用户权利、投诉与争议处理规则',
      summary: '提供个人信息、账户、内容、推荐结果、订阅与安全问题的处理渠道。',
      sections: [
        ['提交请求', '可联系所属院校管理员，或直接使用实际部署公告中的个人信息保护和投诉联系方式。说明请求类别、账户标识、涉及内容及希望采取的措施。请通过受控渠道提供必要身份核验材料，勿发送密码和 Key。'],
        ['可请求事项', '包括查阅、复制、更正、删除、撤回同意、注销、解释推荐结果、请求人工复核，或投诉侵权、异常扣减、未授权访问等问题。运营方在核验权限后按适用法律和公示的流程反馈。拒绝处理时，应在法律要求的范围内说明理由及救济渠道。'],
        ['争议解决', '争议可先与所属院校和实际部署运营方沟通。你可依法向有管辖权的机关投诉、举报，或向有管辖权的人民法院及其他法定争议解决机构寻求救济。'],
      ],
    },
  ]),
  'en-US': documentSet('Updated', [
    {
      id: 'terms',
      title: 'AcademicNexus Terms of Service',
      summary: 'Applies to authorized institutions and their accounts, academic profiles, matching, resources, subscriptions, and AI assistance.',
      sections: [
        ['Service and operator', 'Each deployment operator provides AcademicNexus to partner institutions. Its service notice identifies the operator, the parties responsible for personal information, and their contact details. Self-hosted operators provide their own notices. Review and acknowledge these terms and the Privacy Policy separately during activation.'],
        ['Accounts, workspaces, and access', 'Students and mentors activate a preregistered account using the Access Key on their receipt. Provide accurate information and protect credentials. An academic user with an administrator assignment uses one account to switch workspaces. Role and institution scope govern each action. Account sharing, impersonation, and bypassing controls or quotas are prohibited.'],
        ['Institutional use', 'Follow applicable law, institutional policy, intellectual-property rights, and academic integrity rules. Unauthorized data collection, harassment, fraud, privacy violations, and disruption of the hosted service are prohibited. Mutual selection follows the recorded status and institutional rules. Matching scores, notifications, and AI suggestions support human judgment.'],
        ['Changes and rights', 'The operator may make necessary adjustments, record security events, or restrict abusive accounts for maintenance, safety, or legal obligations and give notice through an appropriate channel. Material changes affecting users receive appropriate notice and, where required by law, renewed consent. Mandatory rights and liabilities follow applicable law.'],
      ],
    },
    {
      id: 'privacy',
      title: 'Privacy Policy',
      summary: 'Describes account and contact data, processing by external services, and how to exercise personal-information rights.',
      sections: [
        ['Responsible parties and contact', 'The deployment notice identifies the personal-information handlers, contact details, hosting region, and the respective responsibilities of the institution and operator. You can also route a request through your institution administrator.'],
        ['Data sources, purposes, and scope', 'Institutions provide names, academic IDs, institution and department details, and preregistered roles. Activation processes the account name, Access Key verification data, password hash, and the times you acknowledge the terms and Privacy Policy. Students and mentors provide an email address and WeChat ID during setup. Phone numbers are optional. As relevant to features you use, we process academic profiles, resources, mutual selection, subscriptions and credits, notifications, AI conversations, and necessary security records to operate those features, secure the service, and fulfill applicable obligations.'],
        ['Service access and contact', 'Email, phone, and WeChat are hidden by default. You can share each field with users in your institution. Institution administrators can read shared contact fields within their assigned scope. Super administrators may view or correct contact data of ordinary student and mentor accounts for account administration. Administrator accounts have no contact editing feature and their details are hidden in the academic contact feature. Email opens in your local mail client. Copying writes to your device clipboard. The applicable client and service govern actual sending and its records.'],
        ['External models, ranking, and disclosures', 'AI conversations may send your request, recent turns, and relevant profile, resource, or candidate context to the selected configured provider, such as DeepSeek, MiniMax, OpenAI, or Qwen. If you select a same-institution contact for drafting, the disclosed detail for that channel can be supplied for that request. When semantic ranking is enabled, selected academic text may be processed by SiliconFlow. Each deployment should disclose the actual recipients, purposes, methods, categories, retention arrangements, and regions. Separate consent, assessments, and cross-border procedures must be completed in advance where legally required.'],
        ['Retention, protection, and your rights', 'The deployment retains account, resource, conversation, and business records according to processing purposes, its published retention periods, and legal obligations. You can update editable records and sharing settings and delete your own AI conversations. Deletion in the application does not directly erase third-party records retained under their rules or applicable law. For access, copying, correction, deletion, consent withdrawal, account closure, and complaints, see User Rights, Complaints, and Disputes.'],
      ],
      links: [{ label: 'Personal Information Protection Law (Chinese)', href: privacyLaw }],
    },
    {
      id: 'ai',
      title: 'AI Services and Algorithmic Assistance',
      summary: 'Explains model providers, matching, generated-content labels, and mutual-selection action cards.',
      sections: [
        ['Model and input', 'Choose from the models configured for the deployment. The platform sends the conversation and context needed for the task. Keep passwords, Keys, unauthorized personal data, and unrelated sensitive information out of prompts. Contact drafting checks the selected channel against the recipient’s sharing settings. Review drafts before sending them in the relevant client.'],
        ['Verification and labeling', 'Model replies in chat are marked “AI-generated”. They may contain errors in facts, reasoning, sources, or citations. When copying for external use, publishing, or submitting work, check facts, sources, personal data, and permissions. Keep or add appropriate AI labels and disclosures when applicable rules or institutional policies require them.'],
        ['Ranking and mutual selection', 'Academic profile information informs relevance rankings. You can correct a profile, filter candidates, and decide whether to act. The platform creates action cards using institution, role, and workflow state. The action is submitted only when you press the button, and the server checks permission and quota again. Authorized people make decisions on admission, assessment, and other significant matters under applicable rules.'],
        ['Feedback', 'Report concerns about recommendations, infringing content, bias, inaccurate output, or security through your institution administrator. Include the time and enough detail to locate the issue, with unrelated information removed.'],
      ],
      links: [{ label: 'Measures for Labeling AI-Generated and Synthesized Content (Chinese)', href: aiLabelRule }],
    },
    {
      id: 'subscription',
      title: 'Subscription Rules',
      summary: 'Explains plans, credit usage, institution inventory, Keys, and delivery.',
      sections: [
        ['Plans and cycles', 'Basic, Pro, Ultra, and Max begin each cycle with 10, 50, 100, and 200 AI credits respectively. Light and standard modes use one credit per successful request. Expert mode uses two. A basic cycle begins at registration and an advanced cycle at activation. An advanced subscription returns to basic after expiry. See your subscription page for the current plan, balance, and dates.'],
        ['Allocation, issuance, and recall', 'Super administrators allocate inventory and can send reminders to a designated institution’s active administrators. Authorized institution administrators issue and deliver Keys within their scope and receive system notifications and reminders. A Key can be redeemed once by an eligible account at its assigned institution. Redemptions cannot be stacked within an active advanced cycle. An unused Key can be recalled and returned to inventory. The recall feature cannot revoke a redeemed Key.'],
        ['Delivery', 'Download the Excel receipt when issuing Keys. Import it into delivery to validate Keys, directly activate an eligible named account, or export a named or general PDF notice. Direct activation consumes the Key. Exporting a PDF leaves the Key state as it was. A general PDF names no account and is handled under institution rules.'],
        ['Payments and questions', 'This version distributes institution entitlements and offers no in-app consumer payment, direct debit, or auto-renewal. Ask your institution to check delivery, credits, or unexpected deductions. Keep Keys out of public channels and do not trade them.'],
      ],
    },
    {
      id: 'content',
      title: 'Copyright, Source Code, and Content Rules',
      summary: 'Explains the repository’s licensing status, third-party rights, and the use of academic user content.',
      sections: [
        ['Project source and copyright', 'The AcademicNexus GitHub repository is publicly visible. The project currently has no open-source license. Applicable rights are reserved by their respective holders. Viewing or forking on GitHub is subject to GitHub’s terms. Copying, modification, redistribution, deployment, and commercial use require a basis in applicable law or permission from the relevant rights holder. Service access is governed by these terms or institutional authorization.'],
        ['Third-party components and identifiers', 'Third-party libraries, fonts, icons, and materials remain subject to their own licenses, attribution terms, and rights notices. The project’s statement concerns rights in its original work. The project name, logos, and institution identifiers remain subject to applicable rights and permissions.'],
        ['User content and resources', 'You retain rights in original content you are entitled to submit. Make sure you have permission to provide profile information or upload resources. You allow the deployment to store, process, and display your content to authorized users as necessary for the functions you use. Respect the distribution restrictions on papers, course materials, and other people’s data.'],
        ['AI output and complaints', 'Check sources, protected expression, third-party rights, and academic integrity rules before using generated output. Rights holders can provide the location of the content, the rights at issue, and necessary evidence through the institution’s contact channel.'],
      ],
      links: [
        { label: 'Project repository on GitHub', href: PROJECT_REPOSITORY },
        { label: 'Computer Software Protection Regulations (Chinese)', href: copyrightRule },
      ],
    },
    {
      id: 'security',
      title: 'Security and Key Protection',
      summary: 'Protects account credentials, activation receipts, subscription receipts, and offline files.',
      sections: [
        ['Accounts and security records', 'Passwords are verified using hashes. Sessions expire. Password changes, administrator resets, and account deactivation invalidate prior sessions. The platform uses role and institution checks, request limits, and necessary administrator audit records. Use a unique password and sign out on shared devices.'],
        ['Account receipts and subscription Keys', 'Access Keys and subscription Keys are verified using hashes and fingerprints. If an unsigned-up account loses its receipt, a super administrator can issue a fresh Excel receipt. Its previous Access Key and incomplete registration session are invalidated. The subscription receipt is available when the Key is issued and can later be imported for validation and delivery.'],
        ['Offline files and incident reporting', 'Receipts and PDFs may contain personal information or redeemable credentials. Distribute them only to authorized recipients, hold them in controlled storage, and remove them when no longer needed. Report lost files, misdelivery, or suspected unauthorized access promptly. Institutions and operators should take applicable verification, containment, notification, and protective measures.'],
      ],
    },
    {
      id: 'minors',
      title: 'Protection of Minors',
      summary: 'Explains safeguards for minors and how guardians can raise requests.',
      sections: [
        ['Eligibility and guardians', 'Institutions should establish safeguards suited to age, the use case, and applicable law before granting access to minors. Processing personal information of children under fourteen requires consent from a parent or other guardian and specific processing rules. The deployment provides the applicable notices and verification process.'],
        ['Personal information and AI', 'Institutions, guardians, and users should limit collection, display, and sharing of minors’ information. Keep unnecessary identity and contact details and other sensitive information out of resources and external AI requests. Report harmful content, harassment, and improper disclosure through your institution.'],
        ['Guardian requests', 'Guardians may request access, correction, deletion, restriction, or consent withdrawal through the responsible party named in the deployment notice or the institution. The recipient verifies identity and guardianship before disclosing protected information.'],
      ],
      links: [{ label: 'Personal Information Protection Law (Chinese)', href: privacyLaw }],
    },
    {
      id: 'storage',
      title: 'Local Storage and Sessions',
      summary: 'Lists the information kept in your browser and how to clear it.',
      sections: [
        ['Browser storage', 'Local storage retains the access token, a copy of account details including contact fields returned for your own account, your language, and your AI provider preference. Session storage holds the temporary registration token and role. The delivery page holds the subscription Key in page memory. Downloaded Excel and PDF files are stored by your browser or device.'],
        ['Clearing data and client controls', 'Signing out removes login and temporary registration data saved by the app. Clear site data to remove language and provider preferences. Manage downloaded files, clipboard data, and local mail drafts in the relevant device or client. Clearing browser data does not clear server-side records.'],
      ],
    },
    {
      id: 'rights',
      title: 'User Rights, Complaints, and Disputes',
      summary: 'Covers personal information, accounts, content, recommendations, subscriptions, and security.',
      sections: [
        ['Submit a request', 'Contact your institution administrator or use the privacy and complaint contacts listed in the deployment notice. Identify your account, the issue, any relevant content, and the outcome you seek. Provide necessary verification through an authorized channel and keep passwords and Keys out of requests.'],
        ['What you can request', 'You can request access, copying, correction, deletion, consent withdrawal, account closure, explanations of recommendations, or human review. You can also report infringement, unusual deductions, or unauthorized access. The operator verifies authorization and responds under applicable law and its published procedure. When required by law, it will explain a denial and available remedies.'],
        ['Disputes', 'You can first contact your institution and the deployment operator. You may also report issues to the competent authority or seek remedies from a court or other legally authorized dispute-resolution body with jurisdiction.'],
      ],
    },
  ]),
}

export function legalDocument(locale: keyof typeof legalDocuments, id?: string): LegalDocument | undefined {
  return legalDocuments[locale].find(item => item.id === id)
}
