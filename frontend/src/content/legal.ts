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

export interface LegalDocument {
  id: LegalDocumentId
  title: string
  eyebrow: string
  summary: string
  sections: { title: string; paragraphs: string[]; bullets?: string[] }[]
}

const effective = '2026-08-23 · v1.1'

export const legalDocuments: Record<'zh-CN' | 'en-US', LegalDocument[]> = {
  'zh-CN': [
    {
      id: 'terms',
      eyebrow: '生效日期：' + effective,
      title: '智导未来服务协议',
      summary: '本协议约定账户、院校服务、平台功能及使用者的基本权利和义务。',
      sections: [
        { title: '一、协议主体与适用范围', paragraphs: ['智导未来（AcademicNexus，以下称“平台”）面向已获合作院校授权的学生、教师和管理员提供学术画像、师生匹配、资源管理、AI 学术辅助及订阅权益管理等服务。本协议适用于网站、应用页面、管理后台和与其直接相关的服务功能。账户由院校预登记并通过 Access Key 激活；使用服务即表示你已阅读并同意本协议及相关规则。'] },
        { title: '二、账户与授权', paragraphs: ['你应提供真实、准确、完整的账户资料，并妥善保管密码、Access Key 和订阅 Key。账户仅限本人使用，不得出租、出借、转让、共享或协助他人绕过验证、配额、院校范围和权限控制。院校管理员仅可在授权院校范围内管理学生、教师和订阅事项；超级管理员仅按平台职责管理全局配置。'] },
        { title: '三、可接受使用', paragraphs: ['你应遵守适用法律、学校管理制度、网络秩序和学术诚信要求。不得利用平台实施或协助实施违法、欺诈、骚扰、歧视、侵犯隐私、侵犯知识产权、破坏系统安全、批量抓取、逆向工程、探测他人信息、传播违法有害内容或其他不当行为。'] },
        { title: '四、服务调整与责任边界', paragraphs: ['平台可能因安全、合规、维护、院校要求或功能升级调整、暂停或终止部分服务，并在合理可行范围内进行提示。平台提供的是学术发展辅助工具，不替代院校、教师或专业人士的独立判断；你应对输入内容、使用行为和对输出的最终采用负责。'] },
        { title: '五、违约处理与规则变更', paragraphs: ['发现异常、滥用或违规使用时，平台可依情节采取提醒、限制功能、暂停账户、终止服务、保留必要安全记录并按适用规则配合处置等措施。协议或相关规则发生实质变化时，平台将更新版本和生效日期；继续使用变更后的服务即表示在法律允许范围内接受更新后的规则。'] },
      ],
    },
    {
      id: 'privacy',
      eyebrow: '生效日期：' + effective,
      title: '隐私政策',
      summary: '本政策以目的明确、最小必要、公开透明和安全保障为原则，说明个人信息的处理规则。',
      sections: [
        { title: '一、处理者、场景与依据', paragraphs: ['平台在合作院校授权及适用法律允许的范围内处理提供服务所必需的信息。平台与相关院校应各自在其法定职责和实际控制范围内履行个人信息保护责任；具体部署主体、个人信息保护联络方式和数据存储安排，以院校上线公告及正式服务页面公示的信息为准。处理通常基于提供服务、履行法定义务、维护安全或取得你的有效同意。'] },
        { title: '二、收集的信息与用途', paragraphs: ['我们处理院校预登记的身份与角色信息、登录和安全信息、你填写的学术画像、资源提交信息、师生匹配和选择记录、AI 对话内容、订阅状态及必要的操作审计记录。用途限于身份验证、账户和权限管理、画像与匹配、资源与 AI 服务、订阅交付、故障排查、防欺诈和安全维护。'], bullets: ['请勿在 AI 对话或资源中提交与任务无关的身份证件号码、金融账户、健康信息、密码、Access Key、订阅 Key 或他人未授权信息。', 'AI 对话按账户保存，并受每个账户最多 100 条会话的产品限制。', '平台不会出售个人信息，也不会将其用于与已告知服务无关的营销用途。'] },
        { title: '三、共享、委托与跨境', paragraphs: ['个人信息仅在实现服务所必需的范围内向同一院校内的获授权管理员、你主动选择的匹配对象、依法有权机关或受托服务提供者披露。AI 请求可能由已配置的模型服务提供者处理；提交前请去除不必要的个人信息。若发生需要单独同意的敏感信息处理、对外提供或跨境提供，平台将依法另行告知并取得相应同意或完成适用程序。'] },
        { title: '四、保存、删除与安全', paragraphs: ['信息仅在实现处理目的、满足院校管理需要和履行法定义务所需的最短期限内保存。账户注销、信息删除、保存期限届满或服务停止后，平台将按适用规则删除、匿名化或依法保留必要信息。平台采取角色和院校范围控制、密码哈希、会话失效、Key 指纹校验、访问限制和安全审计等措施，但互联网传输不存在绝对安全。'] },
        { title: '五、你的权利与行使方式', paragraphs: ['你可以在平台内查看、更正部分账户和画像信息、修改密码并管理订阅。对于查阅、复制、更正、删除、撤回同意、注销账户、解释自动化辅助结果或投诉等请求，可先向所属院校管理员提交。平台和院校将在核验身份、适用法律、院校职责及不损害他人合法权益的前提下处理。'] },
      ],
    },
    {
      id: 'ai',
      eyebrow: '生效日期：' + effective,
      title: 'AI 服务与算法辅助说明',
      summary: '本说明明确 AI 学术助手的功能边界、输入输出要求、透明度和人工复核规则。',
      sections: [
        { title: '一、功能定位', paragraphs: ['AI 学术助手可协助学习路径规划、研究准备、资源使用和师生沟通。其输出由模型基于输入生成，具有概率性，可能存在不完整、不准确、过时或不适用于具体情形的内容。输出仅作辅助参考，不构成招生录取、学业评价、处分、医疗、心理、法律、金融或其他高风险领域的最终决定或专业意见。'] },
        { title: '二、输入、输出与人工复核', paragraphs: ['你应仅输入完成任务所必需的信息，避免提交敏感个人信息和机密材料。使用输出前，应自行核验事实、引文、计算、来源、版权归属和适用性。涉及课程作业、论文、项目、申报、评审或教学活动时，应遵守院校关于 AI 使用、署名、引用和披露的具体规则，并保留必要的人工判断。'] },
        { title: '三、算法辅助与选择权', paragraphs: ['画像、匹配和推荐功能依据已授权信息产生辅助性排序或建议，不替代人为审核。你可通过完善、更新或更正相关资料改善建议基础；在适用场景中，可选择不依赖个性化建议或向院校管理员请求解释、人工复核和反馈。平台不应仅凭自动化处理作出对个人权益有重大影响的决定。'] },
        { title: '四、安全治理与反馈', paragraphs: ['不得利用 AI 生成、传播或协助生成违法、仇恨、歧视、欺诈、虚假、侵权、隐私侵害或其他有害内容。发现明显错误、偏见、安全风险或疑似违规内容时，应停止依赖相关输出并向所属院校管理员反馈。平台可对异常或违规使用采取必要的安全处置。'] },
      ],
    },
    {
      id: 'subscription',
      eyebrow: '生效日期：' + effective,
      title: '订阅服务规则',
      summary: '本规则说明普通与高级订阅、额度周期、院校 Key 和离线交付的适用条件。',
      sections: [
        { title: '一、档位与周期', paragraphs: ['普通账户的对话额度为每订阅周期 10 次；Pro、Ultra、Max 高级订阅分别为每周期 50、100、200 次。普通账户以注册日为周期起点；高级订阅以 Key 激活日为周期起点。高级周期结束且未获得新的有效高级权益时，账户回到普通档位，普通周期自最后高级周期截止日重新起算。页面显示的当前档位、余额和周期日期为准。'] },
        { title: '二、Key 的签发与限制', paragraphs: ['高级订阅 Key 由超级管理员向院校分配额度后，由有权院校管理员签发。Key 为一次性、院校绑定凭证，仅可由符合该院校条件的账户激活；不支持在有效高级订阅期间升级、降级或重复激活。已激活 Key 不可撤回；未激活 Key 可由有权管理员收回，收回后永久失效且相应院校额度恢复。'] },
        { title: '三、离线交付', paragraphs: ['为避免平台保存 Key 明文，签发回执仅在签发时以 Excel 形式下载。管理员可将回执导入离线交付页面进行实时核验，选择直接为未订阅账户激活，或导出指定用户/通用 PDF 通知单。直接激活会立即消耗 Key；PDF 导出不改变 Key 状态。通用 PDF 仅标注适用院校、档位和 Key，不指定学生、教师或账户，不能用于直接激活。'] },
        { title: '四、费用与争议', paragraphs: ['当前 Key 机制为院校额度管理和权益交付功能，并非面向个人的在线支付、自动续费或代扣服务。如后续上线支付、发票、退款或自动续费功能，平台将在启用前另行发布适用的价格、支付、取消和退款规则。对 Key、订阅或额度存在疑问时，请及时向所属院校管理员核验，避免转让或公开传播 Key。'] },
      ],
    },
    {
      id: 'content',
      eyebrow: '生效日期：' + effective,
      title: '知识产权与内容规范',
      summary: '本规则明确平台内容、用户提交内容、AI 输出及学术诚信的使用边界。',
      sections: [
        { title: '一、平台权利', paragraphs: ['平台的名称、界面、软件、代码、数据库结构、文档、标识及其他受保护内容，其权利归平台或合法权利人所有。未经书面许可，不得复制、发行、出租、出售、反向工程、镜像、抓取或以其他方式不当利用平台内容与服务。'] },
        { title: '二、用户内容', paragraphs: ['你对依法拥有权利的原创提交内容保留相应权利。为提供、维护和改进你主动使用的功能，你授予平台在必要范围内处理、存储、展示和传输该内容的有限、非排他授权。你应确保已取得上传、共享或处理该内容所需的权利、授权和同意，并自行承担违反前述承诺的责任。'] },
        { title: '三、AI 输出与学术诚信', paragraphs: ['AI 输出不保证独创性、准确性、可用性、无侵权或适合特定用途。你不得将 AI 输出直接冒充为完全由本人独立完成的成果，或规避课程、论文、竞赛、研究与评审中的诚信要求。提交、发布或引用输出前，应进行人工审查、必要改写、事实核验、来源核验及 AI 使用披露。'] },
        { title: '四、投诉处理', paragraphs: ['权利人认为平台内内容侵害其合法权益的，可向所属院校管理员或平台公示的合规渠道提交权利证明、涉嫌侵权内容定位、联系方式和处理请求。平台将按适用规则进行核验并采取必要措施。'] },
      ],
    },
    {
      id: 'security',
      eyebrow: '生效日期：' + effective,
      title: '信息安全与 Key 保护说明',
      summary: '本说明覆盖账户、Access Key、订阅 Key、离线文件与安全事件的基本保护要求。',
      sections: [
        { title: '一、账户保护', paragraphs: ['密码仅以安全哈希形式保存；登录令牌具有有限有效期，密码变更、管理员重置密码或账户停用会使旧会话失效。请使用独立且足够强度的密码，不与他人共享账户，不在公共设备保存登录状态，并及时退出不再使用的设备。'] },
        { title: '二、Key 保护', paragraphs: ['Access Key 和订阅 Key 均使用受保护哈希和指纹完成验证，服务器不保存其明文。订阅 Key 签发后仅通过一次性 Excel 回执交付；离线交付页面在受限请求内存和当前浏览器页面中核验，完成导出、直接激活、刷新或离开页面后清除浏览器持有的 Key。请勿通过聊天、邮件群发、截图、公开文档或非受控群组传播 Key。'] },
        { title: '三、PDF 与设备安全', paragraphs: ['订阅通知单 PDF 含可兑换 Key，应仅通过受控渠道发送给指定对象；通用 PDF 亦应按院校内部制度保存。下载后请妥善加密或受控保管本地文件，避免在共享电脑、公共云盘或无访问控制的群聊中存放。二维码和条码仅便于机器读取 Key，不构成额外认证。'] },
        { title: '四、事件报告与处置', paragraphs: ['如发现账户异常、Key 泄露、误发 PDF、未授权访问、漏洞或疑似数据泄露，请立即修改密码、停止转发相关文件并联系所属院校管理员。院校管理员应限制受影响账户或 Key、保留必要线索，并依院校制度和适用规则启动后续处置。'] },
      ],
    },
    {
      id: 'minors',
      eyebrow: '生效日期：' + effective,
      title: '未成年人保护声明',
      summary: '平台面向院校授权账户；涉及未成年人时，应提供与年龄和场景相适应的额外保护。',
      sections: [
        { title: '一、适用原则', paragraphs: ['平台不以未成年人为独立营销对象。若账户使用者为未成年人，应在监护人同意、院校管理制度和适用法律允许的范围内使用，并由院校、监护人和使用者共同注意网络安全、学术诚信和个人信息保护。'] },
        { title: '二、信息与内容保护', paragraphs: ['管理员和使用者应遵循最小必要原则，避免将未成年人的敏感信息输入 AI 对话、资源或公开资料。不得利用平台向未成年人传播违法有害信息、实施诱导消费、欺凌、骚扰或其他损害身心健康的活动。'] },
        { title: '三、监护与反馈', paragraphs: ['监护人或院校发现未成年人账户、内容或个人信息存在风险时，可通过所属院校管理员提出核验、限制、删除或其他合理请求。平台将结合身份核验、适用规则和安全需要处理。'] },
      ],
    },
    {
      id: 'storage',
      eyebrow: '生效日期：' + effective,
      title: '本地存储与登录状态说明',
      summary: '本说明公开网站使用的浏览器本地存储、会话存储及其清除方式。',
      sections: [
        { title: '一、当前使用的本地数据', paragraphs: ['为维持登录和语言偏好，网站在浏览器本地存储中保存访问令牌、必要的账户展示信息和语言设置；注册流程的临时令牌保存在会话存储中。订阅 Key 不写入浏览器持久化存储，离线交付页面中的 Key 仅存在于当前页面的运行内存。'] },
        { title: '二、你的控制', paragraphs: ['你可以通过退出登录清除平台写入的访问令牌、账户展示信息和注册临时信息；也可以在浏览器设置中清除本站点数据。清除本地数据会退出登录或中断未完成的注册，但不会自动删除服务器中依法保存的账户或业务信息。'] },
        { title: '三、安全提醒', paragraphs: ['本地存储依赖你的浏览器和设备安全。请不要在不受信任或多人共用的设备保持登录，不要安装来源不明的浏览器扩展，并及时更新浏览器。平台如增加 Cookie、分析工具或其他存储技术，将在启用前更新本说明和隐私政策。'] },
      ],
    },
    {
      id: 'rights',
      eyebrow: '生效日期：' + effective,
      title: '用户权利、投诉与争议处理规则',
      summary: '本规则提供个人信息、服务、内容和安全问题的申诉、投诉与处理路径。',
      sections: [
        { title: '一、请求渠道', paragraphs: ['你可通过所属院校管理员提交账户、个人信息、订阅、内容、AI 输出或安全问题的请求。请求应说明账户标识、事项、事实、希望的处理方式及必要证明；请勿在请求中重复提交密码、Access Key 或订阅 Key。院校管理员可在其授权范围内处理，必要时转交平台进行协同。'] },
        { title: '二、处理原则', paragraphs: ['平台将按身份核验、授权范围、问题性质、适用法律和院校制度处理请求。对合理的查阅、更正、删除、撤回同意、解释、投诉和举报请求，平台将在合理期限内反馈处理状态；法律法规另有规定、涉及他人权益、公共安全、证据保全或无法验证身份的情形除外。'] },
        { title: '三、争议解决', paragraphs: ['服务使用中发生争议时，建议先通过院校管理员和平台公示的联络渠道协商解决。无法协商的，任何一方可依法向有管辖权的人民法院或其他法定争议解决机构寻求救济。适用法律另有强制规定的，从其规定。'] },
      ],
    },
  ],
  'en-US': [
    {
      id: 'terms',
      eyebrow: 'Effective: ' + effective,
      title: 'AcademicNexus Terms of Service',
      summary: 'These terms set out the basic rights and duties for accounts, institution services, and platform use.',
      sections: [
        { title: '1. Parties and scope', paragraphs: ['AcademicNexus provides academic portraits, student-mentor matching, resources, AI academic assistance, and subscription administration to students, mentors, and administrators authorized by partner institutions. These terms apply to the website, application pages, administration console, and related functions. Accounts are pre-registered by an institution and activated with an Access Key.'] },
        { title: '2. Accounts and authorization', paragraphs: ['Keep account information accurate and protect passwords, Access Keys, and subscription Keys. Accounts are personal and may not be rented, lent, transferred, shared, or used to bypass verification, quotas, institution scope, or permission controls. Institution administrators may act only within their assigned institution; super administrators act only within their platform duties.'] },
        { title: '3. Acceptable use', paragraphs: ['Comply with applicable law, institutional rules, network-order rules, and academic-integrity standards. Do not use the platform for unlawful conduct, fraud, harassment, discrimination, privacy invasion, intellectual-property infringement, system attacks, scraping, reverse engineering, unauthorized data access, or harmful content.'] },
        { title: '4. Changes and responsibility', paragraphs: ['The platform may adjust, suspend, or discontinue functions for security, compliance, maintenance, institutional requirements, or upgrades, with notice where reasonably practicable. The platform is an academic-support tool and does not replace independent institutional, teacher, or professional judgment. You remain responsible for your inputs, conduct, and final use of outputs.'] },
        { title: '5. Enforcement and changes', paragraphs: ['For abnormal, abusive, or non-compliant use, the platform may warn, restrict functions, suspend an account, end service, preserve necessary security records, and cooperate with lawful handling as appropriate. Material rule changes will carry an updated version and effective date.'] },
      ],
    },
    {
      id: 'privacy',
      eyebrow: 'Effective: ' + effective,
      title: 'Privacy Policy',
      summary: 'This policy explains personal-information processing using purpose limitation, necessity, transparency, and security safeguards.',
      sections: [
        { title: '1. Controller, context, and basis', paragraphs: ['The platform processes information needed to provide its services within partner-institution authorization and applicable law. The platform and relevant institutions must each fulfill personal-information obligations within their legal duties and actual control. The deployment entity, privacy contact, and storage arrangement are those published in the institution launch notice and formal service page. Processing generally relies on service provision, legal obligations, security, or valid consent.'] },
        { title: '2. Information and purposes', paragraphs: ['We process institution pre-registration identity and role information, login and security data, academic portraits, resource submissions, matching and selection records, AI conversations, subscription status, and necessary operational audit data. These support authentication, account and permission administration, matching, resources, AI assistance, subscription delivery, fraud prevention, and security maintenance.'], bullets: ['Do not enter unrelated identity-document numbers, financial or health information, passwords, Access Keys, subscription Keys, or another person’s data without authorization.', 'AI conversations are retained under the account and capped at 100 conversations per account.', 'We do not sell personal information or use it for unrelated marketing.'] },
        { title: '3. Sharing, processors, and cross-border transfer', paragraphs: ['Information is disclosed only when necessary to authorized same-institution administrators, a matching party you choose, lawful authorities, or contracted service providers. AI requests may be processed by a configured model provider; remove unnecessary personal information before submission. Where sensitive-information processing, external provision, or cross-border transfer requires separate consent or another procedure, we will provide further notice and complete the applicable step.'] },
        { title: '4. Retention and security', paragraphs: ['Information is kept only for the shortest period necessary for the stated purpose, institutional management, and legal obligations. Following deletion, account closure, expiry, or service termination, information is deleted, anonymized, or retained as legally required. We apply role and institution scopes, password hashing, session invalidation, Key fingerprints, access controls, and security auditing, but no internet transmission is absolutely secure.'] },
        { title: '5. Your rights', paragraphs: ['You can view and correct certain account and portrait information, change a password, and manage subscriptions in the platform. For access, copy, correction, deletion, withdrawal of consent, account closure, an explanation of automated assistance, or a complaint, submit a request through your institution administrator. Requests are handled subject to identity verification, applicable law, institutional duties, and protection of others’ rights.'] },
      ],
    },
    {
      id: 'ai',
      eyebrow: 'Effective: ' + effective,
      title: 'AI Service and Algorithmic Assistance Notice',
      summary: 'This notice defines the AI assistant’s purpose, limits, input and output safeguards, transparency, and human-review rules.',
      sections: [
        { title: '1. Purpose', paragraphs: ['The AI academic assistant can support learning pathways, research preparation, resource use, and student-mentor communication. Its output is probabilistic and may be incomplete, inaccurate, outdated, or unsuitable for a particular case. It is assistance only and is not a final decision or professional opinion for admission, academic assessment, discipline, medical, mental-health, legal, financial, or other high-impact matters.'] },
        { title: '2. Inputs, outputs, and human review', paragraphs: ['Submit only information necessary for the task. Before using output, verify facts, citations, calculations, sources, copyright status, and suitability. For coursework, papers, projects, applications, assessment, or teaching, comply with institutional AI-use, authorship, citation, and disclosure rules and retain appropriate human judgment.'] },
        { title: '3. Algorithmic assistance and choice', paragraphs: ['Portrait, matching, and recommendation features produce supportive rankings or suggestions from authorized information and do not replace human review. You may improve the basis by updating or correcting relevant information and, where available, choose not to rely on personalized suggestions or request an explanation, human review, or feedback through an institution administrator. The platform should not make a decision with a major impact on an individual solely through automated processing.'] },
        { title: '4. Safety and feedback', paragraphs: ['Do not use AI to generate, distribute, or facilitate unlawful, hateful, discriminatory, fraudulent, false, infringing, privacy-invasive, or otherwise harmful content. Stop relying on an output that appears erroneous, biased, unsafe, or non-compliant, and report it to your institution administrator. The platform may take necessary safety measures for abnormal or non-compliant use.'] },
      ],
    },
    {
      id: 'subscription',
      eyebrow: 'Effective: ' + effective,
      title: 'Subscription Service Rules',
      summary: 'These rules explain basic and premium plans, entitlement cycles, institution Keys, and offline delivery.',
      sections: [
        { title: '1. Tiers and cycles', paragraphs: ['The basic account allowance is 10 conversations per subscription cycle. Pro, Ultra, and Max allowances are 50, 100, and 200 conversations respectively. A basic cycle begins on the registration date. A premium cycle begins when a Key is redeemed. When a premium cycle ends without a new valid premium entitlement, the account returns to the basic tier and the basic cycle starts on the last premium cycle end date. The plan, balance, and dates shown on the Subscription page control.'] },
        { title: '2. Key issue and limits', paragraphs: ['A super administrator allocates premium inventory to an institution, and an authorized institution administrator issues Keys. Each Key is one-time and institution-bound. It may only be redeemed by an eligible account in that institution. A user cannot upgrade, downgrade, or activate another premium plan during an active premium subscription. Activated Keys cannot be reclaimed; an unused Key may be reclaimed by an authorized administrator, after which it is permanently invalid and the institution inventory is restored.'] },
        { title: '3. Offline delivery', paragraphs: ['To avoid retention of plain-text Keys, an issue receipt is downloaded as an Excel workbook only at issue time. An administrator can import that receipt into the offline-delivery page for live validation, directly activate an unsubscribed account, or export a named-user or general PDF notice. Direct activation consumes the Key immediately; PDF export does not change Key status. A general PDF states the institution, tier, and Key but does not name a student, mentor, or account, and cannot be used for direct activation.'] },
        { title: '4. Charges and questions', paragraphs: ['The current Key mechanism is institution inventory and entitlement delivery, not an individual online-payment, recurring-billing, or automatic-debit service. If payment, invoice, refund, or recurring-billing functions are introduced, applicable price, payment, cancellation, and refund terms will be published before activation. Ask your institution administrator to verify any Key, entitlement, or allowance question promptly.'] },
      ],
    },
    {
      id: 'content',
      eyebrow: 'Effective: ' + effective,
      title: 'Intellectual Property and Content Rules',
      summary: 'These rules set boundaries for platform materials, user content, AI outputs, and academic integrity.',
      sections: [
        { title: '1. Platform rights', paragraphs: ['The platform name, interface, software, code, database structure, documentation, identifiers, and other protected materials belong to the platform or the lawful rights holder. Without written permission, do not copy, distribute, rent, sell, reverse engineer, mirror, scrape, or otherwise improperly use platform materials or services.'] },
        { title: '2. User content', paragraphs: ['You retain rights in original content that you lawfully own. To provide, maintain, and improve the function you choose to use, you grant the platform a limited, non-exclusive authorization to process, store, display, and transmit that content as necessary. You must have the rights, permissions, and consents needed to upload, share, or process the content.'] },
        { title: '3. AI outputs and academic integrity', paragraphs: ['AI outputs are not guaranteed to be original, accurate, fit for purpose, non-infringing, or available for a particular use. Do not present AI output as entirely independent work where this would breach course, paper, competition, research, or assessment integrity rules. Conduct human review, verification, appropriate rewriting, source review, and AI-use disclosure before submission or publication.'] },
        { title: '4. Rights complaints', paragraphs: ['A rights holder who believes content on the platform infringes lawful rights may submit proof of rights, a location of the disputed content, contact details, and a requested action to an institution administrator or the platform’s published compliance channel. The platform will verify and take necessary measures under applicable rules.'] },
      ],
    },
    {
      id: 'security',
      eyebrow: 'Effective: ' + effective,
      title: 'Information Security and Key Protection Notice',
      summary: 'This notice covers accounts, Access Keys, subscription Keys, offline files, and basic incident response.',
      sections: [
        { title: '1. Account protection', paragraphs: ['Passwords are stored only as secure hashes. Login tokens are time-limited, and password changes, administrator password resets, or account deactivation invalidate older sessions. Use a strong unique password, do not share accounts, avoid staying signed in on public devices, and sign out of devices you no longer use.'] },
        { title: '2. Key protection', paragraphs: ['Access Keys and subscription Keys are verified using protected hashes and fingerprints; their plain text is not retained on the server. A subscription Key is delivered only in a one-time Excel receipt. The offline-delivery page validates the receipt in bounded request memory and the current browser page, then clears browser-held Key data after export, direct activation, refresh, or navigation. Never distribute a Key through public documents, screenshots, bulk email, or uncontrolled groups.'] },
        { title: '3. PDF and device security', paragraphs: ['A subscription PDF includes a redeemable Key and should be sent only through a controlled channel to its intended person. General PDFs should also be retained according to institutional rules. Protect downloaded files locally and avoid shared devices, public cloud folders, and group chats without access control. QR and barcode representations only assist machine reading and do not add authentication.'] },
        { title: '4. Incident response', paragraphs: ['If you suspect account misuse, Key exposure, a misdirected PDF, unauthorized access, a vulnerability, or a data incident, change the password, stop forwarding the relevant file, and contact your institution administrator immediately. Administrators should restrict affected accounts or Keys, preserve necessary evidence, and follow institutional and applicable incident procedures.'] },
      ],
    },
    {
      id: 'minors',
      eyebrow: 'Effective: ' + effective,
      title: 'Minor Protection Statement',
      summary: 'The platform is for institution-authorized accounts and applies additional safeguards where a user is a minor.',
      sections: [
        { title: '1. Principle', paragraphs: ['The platform is not marketed to minors as an independent consumer service. A minor may use it only with guardian consent, institutional rules, and applicable law. Institutions, guardians, and users should jointly protect online safety, academic integrity, and personal information.'] },
        { title: '2. Information and content', paragraphs: ['Administrators and users should follow data minimization and avoid entering a minor’s sensitive information into AI conversations, resources, or public materials. The platform must not be used to deliver harmful content, induce spending, bully, harass, or otherwise harm a minor’s physical or mental wellbeing.'] },
        { title: '3. Guardian and institution requests', paragraphs: ['A guardian or institution may ask an institution administrator to verify, restrict, delete, or otherwise address risk involving a minor’s account, content, or personal information. The request will be handled with identity verification, applicable rules, and security needs.'] },
      ],
    },
    {
      id: 'storage',
      eyebrow: 'Effective: ' + effective,
      title: 'Local Storage and Login-State Notice',
      summary: 'This notice discloses browser local storage, session storage, and how they are cleared.',
      sections: [
        { title: '1. Current local data', paragraphs: ['To maintain sign-in and language preference, the website stores an access token, necessary account-display information, and language settings in browser local storage. A registration token is stored in session storage for the registration flow. Subscription Keys are not written to persistent browser storage; Keys on the offline-delivery page exist only in the running memory of the current page.'] },
        { title: '2. Your controls', paragraphs: ['Sign out to remove the platform’s access token, account-display data, and registration-session information. You can also clear this site’s data in browser settings. Clearing local data signs you out or interrupts unfinished registration, but does not automatically delete account or business information lawfully retained on the server.'] },
        { title: '3. Security reminder', paragraphs: ['Local storage depends on your browser and device security. Do not remain signed in on untrusted or shared devices, avoid unknown browser extensions, and keep the browser up to date. If the platform introduces cookies, analytics, or other storage technologies, this notice and the Privacy Policy will be updated before use.'] },
      ],
    },
    {
      id: 'rights',
      eyebrow: 'Effective: ' + effective,
      title: 'User Rights, Complaints, and Dispute Handling',
      summary: 'This rule provides a route for personal-information, service, content, AI-output, and security requests.',
      sections: [
        { title: '1. Request route', paragraphs: ['Submit account, personal-information, subscription, content, AI-output, or security requests through your institution administrator. State the account identifier, issue, facts, requested action, and necessary proof, but do not repeat a password, Access Key, or subscription Key. An institution administrator may handle matters within their authorization and escalate matters to the platform when needed.'] },
        { title: '2. Handling principles', paragraphs: ['Requests are handled according to identity verification, authorization scope, issue type, applicable law, and institutional rules. The platform will provide a status response within a reasonable time for appropriate access, correction, deletion, consent withdrawal, explanation, complaint, or report requests, except where law provides otherwise or identity cannot be verified, another person’s rights would be harmed, or preservation or public-safety needs apply.'] },
        { title: '3. Dispute resolution', paragraphs: ['For a dispute, first seek resolution through the institution administrator and the platform’s published contact route. If it cannot be resolved, either party may seek relief from a court or other lawful dispute-resolution body with jurisdiction, subject to mandatory applicable rules.'] },
      ],
    },
  ],
}

export function legalDocument(locale: 'zh-CN' | 'en-US', id?: string): LegalDocument | undefined {
  return legalDocuments[locale].find(item => item.id === id)
}
