// AIWriteX 主JavaScript文件  
  
class AIWriteXApp {  
    constructor() {
        this.ws = null;
        this.currentView = 'creative-workshop';
        this.isGenerating = false;
        this.creativeWorkshopInitialized = false;
        this.templateCategories = [];
        this.currentTemplateCategory = '随机分类';
        this.currentTemplates = [];
        this.statusPoller = null;
        this.statusIndicator = null;
        this.manualStop = false;
        this.logPanelInitialized = false;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.showView(this.currentView);

        this.statusIndicator = document.getElementById('generation-status');
        this.updateStatusIndicator('等待配置', 'status-idle');

        // 等待配置管理器初始化完成后再加载配置
        this.waitForConfigManager();
    }
      
    waitForConfigManager() {  
        if (window.configManager) {  
            this.loadInitialData();  
        } else {  
            setTimeout(() => this.waitForConfigManager(), 100);  
        }  
    }  
      
    loadInitialData() {  
        // 根据当前视图加载相应数据  
        switch (this.currentView) {
            case 'creative-workshop':
                this.initializeCreativeWorkshop();
                this.loadDimensionalConfig();
                break;
            case 'article-manager':
                this.loadArticles();
                break;
            case 'config-manager':  
                // 配置已由 configManager 自动加载  
                break;  
        }  
    }  
      
    setupEventListeners() {  
        // 原有的导航菜单点击事件（排除系统配置的切换按钮）  
        document.querySelectorAll('.nav-link:not(.nav-toggle)').forEach(link => {  
            link.addEventListener('click', (e) => {  
                e.preventDefault();  
                const view = link.dataset.view;  
                this.showView(view);  
            });  
        });  
    
        // 系统配置主菜单切换
        const navToggle = document.querySelector('.nav-toggle');
        if (navToggle) {
            navToggle.addEventListener('click', (e) => {
                e.preventDefault();
                const navItem = e.target.closest('.nav-item-expandable');
                if (navItem) {  
                    navItem.classList.toggle('expanded');  
                }  
                this.showView('config-manager');  
            });  
        }  
    
        // 配置二级菜单点击事件  
        document.querySelectorAll('.nav-sublink').forEach(link => {  
            link.addEventListener('click', (e) => {  
                e.preventDefault();  
                const configType = link.dataset.config;  
                
                // 更新二级菜单状态  
                document.querySelectorAll('.nav-sublink').forEach(sublink => {  
                    sublink.classList.remove('active');  
                });  
                link.classList.add('active');  
                
                // 显示对应配置面板  
                this.showConfigPanel(configType);  
            });  
        });  
    
        // 生成按钮事件  
        const generateBtn = document.getElementById('generate-btn');  
        if (generateBtn) {  
            generateBtn.addEventListener('click', () => this.startGeneration());  
        }  
    
        // 停止按钮事件  
        const stopBtn = document.getElementById('stop-btn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopGeneration());
        }

        const clearLogBtn = document.getElementById('clear-log-btn');
        if (clearLogBtn) {
            clearLogBtn.addEventListener('click', () => this.clearLogPanel());
        }

        // 文章列表刷新
        const refreshArticlesBtn = document.getElementById('refresh-articles');
        if (refreshArticlesBtn) {
            refreshArticlesBtn.addEventListener('click', () => this.loadArticles(true));
        }

        const emptyRefreshBtn = document.getElementById('empty-refresh-btn');
        if (emptyRefreshBtn) {
            emptyRefreshBtn.addEventListener('click', () => this.loadArticles(true));
        }

        // 配置保存事件 - 使用统一配置管理器
        const saveConfigBtn = document.getElementById('save-config-btn');
        if (saveConfigBtn) {
            saveConfigBtn.addEventListener('click', () => this.saveConfig());
        }
    
        // 维度滑块事件  
        document.querySelectorAll('.dimension-slider').forEach(slider => {
            slider.addEventListener('input', (e) => {
                this.updateDimensionValue(e.target);
            });
        });

        const customTopicToggle = document.getElementById('custom-topic-toggle');
        if (customTopicToggle) {
            customTopicToggle.addEventListener('change', (e) => {
                const enabled = e.target.checked;
                this.toggleCustomTopicFields(enabled);
                if (enabled) {
                    const topicInput = document.getElementById('topic-input');
                    if (!topicInput?.value.trim()) {
                        this.updateStatusIndicator('请输入文章标题', 'status-warning');
                    }
                } else {
                    this.updateStatusIndicator('使用热搜模式生成', 'status-idle');
                }
            });
        }

        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            topicInput.addEventListener('input', () => {
                const value = topicInput.value.trim();
                if (value) {
                    this.updateStatusIndicator('自定义话题已就绪', 'status-progress');
                } else if (customTopicToggle?.checked) {
                    this.updateStatusIndicator('请输入文章标题', 'status-warning');
                }
            });
        }

        const templateCategorySelect = document.getElementById('template-category-select');
        if (templateCategorySelect) {
            templateCategorySelect.addEventListener('change', (e) => {
                this.currentTemplateCategory = e.target.value || '随机分类';
                this.loadTemplatesForCategory(this.currentTemplateCategory);
            });
        }

        const templateSelect = document.getElementById('template-select');
        if (templateSelect) {
            templateSelect.addEventListener('change', () => {
                if (customTopicToggle?.checked) {
                    this.updateStatusIndicator('模板已更新', 'status-progress');
                }
            });
        }

        const referenceUrlsInput = document.getElementById('reference-urls-input');
        if (referenceUrlsInput) {
            referenceUrlsInput.addEventListener('input', () => {
                if (customTopicToggle?.checked) {
                    this.updateStatusIndicator('已更新参考素材', 'status-progress');
                }
            });
        }

        const referenceRatioSelect = document.getElementById('reference-ratio-select');
        if (referenceRatioSelect) {
            referenceRatioSelect.addEventListener('change', () => {
                if (customTopicToggle?.checked) {
                    this.updateStatusIndicator('借鉴比例已更新', 'status-progress');
                }
            });
        }
    }

    showConfigPanel(panelType) {  
        const configContent = document.querySelector('.config-content');  
        const targetPanel = document.getElementById(`config-${panelType}`);  
        
        // 立即重置滚动位置  
        if (configContent) {  
            configContent.scrollTop = 0;  
        }  
        
        // 隐藏其他配置面板  
        document.querySelectorAll('.config-panel').forEach(panel => {  
            if (panel !== targetPanel) {  
                panel.classList.remove('active');  
                panel.style.display = 'none';  
            }  
        });  
        
        // 显示目标面板  
        if (targetPanel) {  
            targetPanel.style.display = 'block';  
            targetPanel.offsetHeight; // 强制重排  
            targetPanel.classList.add('active');  
        }  
        
        // 更新导航状态  
        document.querySelectorAll('.config-nav-item').forEach(item => {  
            item.classList.remove('active');  
        });  
        
        const activeNavItem = document.querySelector(`[data-config="${panelType}"]`).parentElement;  
        if (activeNavItem) {  
            activeNavItem.classList.add('active');  
        }  
        
        this.currentPanel = panelType;  
    }
        
    connectWebSocket() {  
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';  
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;  
          
        this.ws = new WebSocket(wsUrl);  
          
        this.ws.onopen = () => {  
            this.updateConnectionStatus(true);  
        };  
          
        this.ws.onmessage = (event) => {  
            // 忽略心跳响应  
            if (event.data === 'pong') {  
                return;  
            }  
            
            try {  
                const data = JSON.parse(event.data);  
                this.addLogEntry(data);  
            } catch (error) {  
                //console.warn('无法解析 WebSocket 消息:', event.data);  
            }  
        };  
          
        this.ws.onclose = () => {  
            this.updateConnectionStatus(false);  
            // 3秒后重连  
            setTimeout(() => this.connectWebSocket(), 3000);  
        };  
          
        this.ws.onerror = (error) => {  
            this.updateConnectionStatus(false);  
        };  
          
        // 发送心跳  
        setInterval(() => {  
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {  
                this.ws.send('ping');  
            }  
        }, 30000);  
    }  
      
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('status-indicator');
        if (indicator) {
            indicator.style.backgroundColor = connected ?
                'var(--success-color)' : 'var(--error-color)';
            const text = indicator.querySelector('.status-text');
            if (text) {
                text.textContent = connected ? '在线' : '离线';
            }
        }
    }
      
    addLogEntry(logData) {
        const logPanel = document.getElementById('log-panel');
        if (!logPanel) return;

        const emptyState = logPanel.querySelector('.log-empty');
        if (emptyState) {
            emptyState.remove();
        }

        const entry = document.createElement('div');
        entry.className = `log-entry ${logData.type}`;

        const timestampValue = typeof logData.timestamp === 'number'
            ? logData.timestamp
            : Date.now() / 1000;
        const timestamp = new Date(timestampValue * 1000).toLocaleTimeString();
        const message = typeof logData.message === 'string' ? logData.message : '';
        entry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <span class="log-message">${this.escapeHtml(message)}</span>
        `;
          
        logPanel.appendChild(entry);  
        logPanel.scrollTop = logPanel.scrollHeight;  
          
        // 限制日志条数  
        const entries = logPanel.querySelectorAll('.log-entry');  
        if (entries.length > 1000) {  
            entries[0].remove();  
        }  
    }  
      
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    clearLogPanel(showPlaceholder = true) {
        const logPanel = document.getElementById('log-panel');
        if (!logPanel) return;

        logPanel.innerHTML = '';

        if (showPlaceholder) {
            const emptyState = document.createElement('div');
            emptyState.className = 'log-empty';
            emptyState.textContent = this.isGenerating
                ? '任务执行中，等待日志...'
                : '等待任务开始...';
            logPanel.appendChild(emptyState);
        }
    }
      
    showView(viewName) {  
        // 更新导航状态  
        document.querySelectorAll('.nav-link').forEach(link => {  
            link.classList.remove('active');  
        });  
        
        requestAnimationFrame(() => {  
            document.querySelectorAll('.nav-link').forEach(link => {  
                if (link.dataset.view === viewName) {  
                    link.classList.add('active');  
                }  
            });  
        });  
        
        const targetView = document.getElementById(`${viewName}-view`);  
        
        // 隐藏其他视图  
        document.querySelectorAll('.view-content').forEach(view => {  
            if (view !== targetView) {  
                view.classList.remove('active');  
                setTimeout(() => {  
                    view.style.display = 'none';  
                }, 200);  
            }  
        });  
        
        // 显示目标视图  
        if (targetView) {  
            targetView.style.display = 'block';  
            requestAnimationFrame(() => {  
                targetView.classList.add('active');  
            });
            
            // 延迟初始化模板管理器  
            if (viewName === 'template-manager' && !window.templateManager) {
                window.templateManager = new TemplateManager();
            }
            if (viewName === 'creative-workshop') {
                this.initializeCreativeWorkshop();
            }
        }

        // 关键修改:如果切换到配置管理视图,默认激活界面设置子菜单
        if (viewName === 'config-manager') {  
            // 清除所有子菜单的active状态  
            document.querySelectorAll('.nav-sublink').forEach(sublink => {  
                sublink.classList.remove('active');  
            });  
            
            // 激活界面设置子菜单  
            const uiConfigSublink = document.querySelector('[data-config="ui"]');  
            if (uiConfigSublink) {  
                uiConfigSublink.classList.add('active');  
            }  
            
            // 显示界面设置面板  
            if (window.configManager) {  
                window.configManager.showConfigPanel('ui');  
            }  
        } else {  
            // 关键:如果切换到非配置管理视图,折叠系统设置菜单  
            const expandableNavItem = document.querySelector('.nav-item-expandable');  
            if (expandableNavItem) {  
                expandableNavItem.classList.remove('expanded');  
            }  
            
            // 同时清除所有子菜单的 active 状态  
            document.querySelectorAll('.nav-sublink').forEach(sublink => {  
                sublink.classList.remove('active');  
            });  
        }  
        
        // 控制预览按钮的显示/隐藏  
        const previewTrigger = document.getElementById('preview-trigger');  
        if (previewTrigger) {  
            const viewsWithPreview = ['creative-workshop', 'article-manager', 'template-manager'];  
            if (viewsWithPreview.includes(viewName)) {  
                previewTrigger.style.display = 'flex';  
            } else {  
                previewTrigger.style.display = 'none';  
            }  
        }  
        
        this.currentView = viewName;

        if (viewName === 'article-manager') {
            this.loadArticles();
        }
    }
      
    async startGeneration() {
        if (this.isGenerating) {
            this.showNotification('任务正在执行中，请稍候', 'warning');
            return;
        }

        const customTopicToggle = document.getElementById('custom-topic-toggle');
        const useCustomTopic = customTopicToggle?.checked ?? false;

        const topicInput = document.getElementById('topic-input');
        const topic = useCustomTopic ? (topicInput?.value.trim() || '') : '';

        if (useCustomTopic && !topic) {
            this.showNotification('请输入文章标题', 'warning');
            topicInput?.focus();
            this.updateStatusIndicator('请输入文章标题', 'status-warning');
            return;
        }

        const categorySelect = document.getElementById('template-category-select');
        const templateSelect = document.getElementById('template-select');
        const ratioSelect = document.getElementById('reference-ratio-select');

        const selectedCategory = categorySelect?.value || '随机分类';
        const selectedTemplate = templateSelect?.value || '随机模板';
        const referenceRatio = parseFloat(ratioSelect?.value || '0.3') || 0.3;

        const referenceData = this.collectReferenceUrls();
        if (referenceData.invalid.length > 0) {
            this.showNotification(`存在无效链接：${referenceData.invalid.join(', ')}`, 'warning');
            this.updateStatusIndicator('请检查参考链接格式', 'status-warning');
            return;
        }

        const payload = {
            topic,
            urls: referenceData.urls,
            reference_ratio: referenceRatio,
            custom_template_category:
                useCustomTopic && selectedCategory !== '随机分类' ? selectedCategory : '',
            custom_template:
                useCustomTopic && selectedTemplate !== '随机模板' ? selectedTemplate : '',
        };

        this.isGenerating = true;
        this.manualStop = false;
        this.clearLogPanel();
        this.updateGenerationUI(true);
        this.updateStatusIndicator('生成任务已提交...', 'status-progress');

        try {
            const response = await fetch('/api/content/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || '生成请求失败');
            }

            if (window.configManager) {
                const config = window.configManager.getConfig();
                config.custom_topic = topic;
                config.urls = referenceData.urls;
                config.reference_ratio = referenceRatio;
                config.custom_template_category = payload.custom_template_category;
                config.custom_template = payload.custom_template;
            }

            this.showNotification('内容生成已开始', 'success');
            this.updateStatusIndicator('生成中...', 'status-progress');
            this.startStatusPolling();
        } catch (error) {
            console.error('生成失败:', error);
            this.isGenerating = false;
            this.updateGenerationUI(false);
            this.updateStatusIndicator('生成失败', 'status-error');
            this.showNotification('生成失败，请重试', 'error');
        }
    }

    async stopGeneration() {
        const wasGenerating = this.isGenerating;
        this.manualStop = true;
        try {
            const response = await fetch('/api/content/stop', {
                method: 'POST'
            });

            if (response.ok) {
                this.showNotification('已停止生成', 'info');
            } else {
                const errorText = await response.text();
                throw new Error(errorText || '停止生成失败');
            }
        } catch (error) {
            console.error('停止生成失败:', error);
            this.showNotification('停止生成失败，请重试', 'error');
        } finally {
            this.clearStatusPoller();
            this.isGenerating = false;
            this.updateGenerationUI(false);
            if (wasGenerating) {
                this.updateStatusIndicator('生成已停止', 'status-warning');
            } else {
                this.manualStop = false;
            }
        }
    }

    updateGenerationUI(isGenerating) {
        const generateBtn = document.getElementById('generate-btn');
        const stopBtn = document.getElementById('stop-btn');

        if (generateBtn) {
            generateBtn.disabled = isGenerating;
            generateBtn.innerHTML = isGenerating
                ? '<i class="icon-sparkles"></i> 生成中...'
                : '<i class="icon-sparkles"></i> 开始生成';
        }

        if (stopBtn) {
            stopBtn.disabled = !isGenerating;
        }

        const customTopicToggle = document.getElementById('custom-topic-toggle');
        if (customTopicToggle) {
            customTopicToggle.disabled = isGenerating;
        }

        const formControls = document.querySelectorAll('#generation-panel input, #generation-panel select, #generation-panel textarea');
        formControls.forEach(control => {
            if (['generate-btn', 'stop-btn'].includes(control.id)) {
                return;
            }

            if (control.id === 'custom-topic-toggle') {
                return;
            }

            if (isGenerating) {
                if (!control.dataset.prevDisabled) {
                    control.dataset.prevDisabled = control.disabled ? 'true' : 'false';
                }
                control.disabled = true;
            } else if (control.dataset.prevDisabled) {
                control.disabled = control.dataset.prevDisabled === 'true';
                delete control.dataset.prevDisabled;
            }
        });

        if (!isGenerating) {
            this.toggleCustomTopicFields(customTopicToggle?.checked ?? false);
        }
    }

    startStatusPolling(interval = 4000) {
        if (!this.isGenerating) {
            return;
        }

        this.clearStatusPoller();

        const poll = async () => {
            if (!this.isGenerating) {
                return;
            }

            try {
                const response = await fetch('/api/content/status');
                if (response.ok) {
                    const status = await response.json();
                    if (!status.is_running) {
                        this.clearStatusPoller();
                        this.isGenerating = false;
                        this.updateGenerationUI(false);
                        if (this.manualStop) {
                            this.manualStop = false;
                        } else {
                            this.updateStatusIndicator('生成完成', 'status-success');
                            this.showNotification('生成任务已完成', 'success');
                            this.loadArticles();
                        }
                        return;
                    }
                }
            } catch (error) {
                console.warn('检测生成状态失败:', error);
            }

            if (this.isGenerating) {
                this.statusPoller = setTimeout(poll, interval);
            }
        };

        poll();
    }

    clearStatusPoller() {
        if (this.statusPoller) {
            clearTimeout(this.statusPoller);
            this.statusPoller = null;
        }
    }

    collectReferenceUrls() {
        const textarea = document.getElementById('reference-urls-input');
        if (!textarea) {
            return { urls: [], invalid: [] };
        }

        const rawEntries = textarea.value
            .split(/\n|\|/)
            .map(item => item.trim())
            .filter(item => item.length > 0);

        const urls = [];
        const invalid = [];

        for (const entry of rawEntries) {
            if (/^https?:\/\//i.test(entry)) {
                if (urls.length < 10) {
                    urls.push(entry);
                }
            } else {
                invalid.push(entry);
            }
        }

        return { urls, invalid };
    }

    toggleCustomTopicFields(enabled) {
        const controls = [
            document.getElementById('topic-input'),
            document.getElementById('template-category-select'),
            document.getElementById('template-select'),
            document.getElementById('reference-urls-input'),
            document.getElementById('reference-ratio-select')
        ];

        controls.forEach(control => {
            if (control) {
                control.disabled = !enabled;
            }
        });

        if (!enabled) {
            this.updateStatusIndicator('使用热搜模式生成', 'status-idle');
        }
    }

    async initializeCreativeWorkshop(forceReload = false) {
        if (!window.configManager || !window.configManager.config) {
            return;
        }

        if (!this.creativeWorkshopInitialized || forceReload || this.templateCategories.length === 0) {
            await this.loadTemplateCategories();
        }

        const config = window.configManager.getConfig() || {};
        const useCustomTopic = Boolean(config.custom_topic);
        const selectedCategory = config.custom_template_category || '随机分类';
        const selectedTemplate = config.custom_template || '随机模板';

        this.populateTemplateCategorySelect(this.templateCategories, selectedCategory);
        await this.loadTemplatesForCategory(selectedCategory, selectedTemplate);

        const topicInput = document.getElementById('topic-input');
        if (topicInput) {
            topicInput.value = config.custom_topic || '';
        }

        const referenceInput = document.getElementById('reference-urls-input');
        if (referenceInput) {
            if (Array.isArray(config.urls) && config.urls.length > 0) {
                referenceInput.value = config.urls.join('\n');
            } else {
                referenceInput.value = '';
            }
        }

        const ratioSelect = document.getElementById('reference-ratio-select');
        if (ratioSelect) {
            const ratioValue = typeof config.reference_ratio === 'number' && config.reference_ratio > 0
                ? config.reference_ratio
                : 0.3;
            const matchedOption = Array.from(ratioSelect.options).find(option => parseFloat(option.value) === ratioValue);
            ratioSelect.value = matchedOption ? matchedOption.value : '0.3';
        }

        const toggle = document.getElementById('custom-topic-toggle');
        if (toggle) {
            toggle.checked = useCustomTopic;
        }

        this.toggleCustomTopicFields(useCustomTopic);

        if (useCustomTopic) {
            if (topicInput?.value.trim()) {
                this.updateStatusIndicator('自定义话题已就绪', 'status-progress');
            } else {
                this.updateStatusIndicator('请输入文章标题', 'status-warning');
            }
        } else {
            this.updateStatusIndicator('使用热搜模式生成', 'status-idle');
        }

        this.creativeWorkshopInitialized = true;
        this.updateGenerationUI(this.isGenerating);

        if (!this.logPanelInitialized) {
            this.clearLogPanel();
            this.logPanelInitialized = true;
        }
    }

    async loadTemplateCategories() {
        try {
            const response = await fetch('/api/config/template-categories');
            if (response.ok) {
                const result = await response.json();
                this.templateCategories = Array.isArray(result.data) ? result.data : [];
            } else {
                this.templateCategories = [];
            }
        } catch (error) {
            console.error('加载模板分类失败:', error);
            this.templateCategories = [];
        }
    }

    async loadTemplatesForCategory(category, preferredTemplate = '') {
        const normalizedCategory = category || '随机分类';
        this.currentTemplateCategory = normalizedCategory;

        if (!normalizedCategory || normalizedCategory === '随机分类') {
            this.currentTemplates = [];
            this.populateTemplateSelect([], preferredTemplate);
            return;
        }

        try {
            const response = await fetch(`/api/config/templates/${encodeURIComponent(normalizedCategory)}`);
            if (response.ok) {
                const result = await response.json();
                this.currentTemplates = Array.isArray(result.data) ? result.data : [];
            } else {
                this.currentTemplates = [];
            }
        } catch (error) {
            console.error('加载模板列表失败:', error);
            this.currentTemplates = [];
        }

        this.populateTemplateSelect(this.currentTemplates, preferredTemplate);
    }

    populateTemplateCategorySelect(categories, selectedCategory) {
        const select = document.getElementById('template-category-select');
        if (!select) return;

        const options = ['随机分类', ...new Set((categories || []).filter(item => item && item.trim()))];

        select.innerHTML = options
            .map(option => `<option value="${option}">${option}</option>`)
            .join('');

        const target = options.includes(selectedCategory) ? selectedCategory : '随机分类';
        select.value = target;
    }

    populateTemplateSelect(templates, selectedTemplate) {
        const select = document.getElementById('template-select');
        if (!select) return;

        const options = ['随机模板', ...(templates || [])];

        select.innerHTML = options
            .map(option => `<option value="${option}">${option}</option>`)
            .join('');

        const target = templates && templates.includes(selectedTemplate) ? selectedTemplate : '随机模板';
        select.value = target;
    }

    updateStatusIndicator(message, statusClass = 'status-idle') {
        if (!this.statusIndicator) {
            this.statusIndicator = document.getElementById('generation-status');
        }

        if (!this.statusIndicator) return;

        this.statusIndicator.textContent = message;
        this.statusIndicator.classList.remove('status-idle', 'status-progress', 'status-success', 'status-error', 'status-warning');
        this.statusIndicator.classList.add(statusClass);
    }
      
    // 使用统一配置管理器保存配置  
    async saveConfig() {  
        if (!window.configManager) {  
            this.showNotification('配置管理器未初始化', 'error');  
            return;  
        }  
        
        try {  
            const success = await window.configManager.saveConfig();  
            
            if (success) {  
                this.showNotification('设置保存成功', 'success');  
            } else {  
                throw new Error('保存失败');  
            }  
        } catch (error) {  
            this.showNotification('设置保存失败', 'error');  
        }  
    }
      
    async loadDimensionalConfig() {    
        // 必须通过配置管理器获取，无回退  
        if (!window.configManager) {  
            console.warn('配置管理器未初始化');  
            return;  
        }    
            
        try {    
            const config = window.configManager.getConfig();    
            if (config.dimensional_creative) {    
                this.updateDimensionalUI(config.dimensional_creative);    
            }    
        } catch (error) {    
            console.error('加载维度配置失败:', error);    
        }    
    }   
        
    updateDimensionValue(slider) {  
        const value = slider.value;  
        const valueDisplay = slider.parentElement.querySelector('.slider-value');  
        if (valueDisplay) {  
            valueDisplay.textContent = value;  
        }  
        
        // 通过配置管理器更新后端内存  
        const dimensionName = slider.dataset.dimension;  
        if (dimensionName && window.configManager) {  
            window.configManager.updateConfig({  
                dimensional_creative: {  
                    ...window.configManager.config.dimensional_creative,  
                    [dimensionName]: parseFloat(value)  
                }  
            });  
        } else {  
            console.warn('配置管理器不可用，无法保存维度配置');  
        }  
    }
      
    updateDimensionalUI(dimensionalConfig) {  
        // 更新维度滑块  
        Object.entries(dimensionalConfig).forEach(([key, value]) => {  
            const slider = document.querySelector(`[data-dimension="${key}"]`);  
            if (slider) {  
                slider.value = value;  
                this.updateDimensionValue(slider);  
            }  
        });  
    }  
      
    async loadArticles(showFeedback = false) {
        // 加载文章列表
        let fetchSuccess = false;
        try {
            const response = await fetch('/api/articles/');
            if (response.ok) {
                const articles = await response.json();
                this.updateArticleGrid(articles);
                fetchSuccess = true;
            }
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('加载文章失败:', error);
            this.showNotification('加载文章列表失败', 'error');
        }

        if (showFeedback && fetchSuccess) {
            this.showNotification('文章列表已刷新', 'success');
        }
    }

    updateArticleGrid(articles) {
        const grid = document.getElementById('article-grid');
        const emptyState = document.getElementById('article-empty-state');
        if (!grid || !emptyState) return;

        grid.innerHTML = '';

        if (!Array.isArray(articles) || articles.length === 0) {
            emptyState.style.display = 'flex';
            grid.style.display = 'none';
            return;
        }

        emptyState.style.display = 'none';
        grid.style.display = 'grid';

        articles.forEach(article => {
            const card = this.createArticleCard(article);
            grid.appendChild(card);
        });
    }

    createArticleCard(article) {
        const card = document.createElement('div');
        card.className = 'article-card';
        const title = this.escapeHtml(article.title || '未命名文章');
        const updatedAt = this.escapeHtml(this.formatDateTime(article.updated_at || article.created_at));
        const formatLabel = this.escapeHtml(article.format || '未知');
        const sizeLabel = this.escapeHtml(this.formatFileSize(article.size_kb));
        const excerpt = this.escapeHtml(article.excerpt || '暂无摘要');
        const statusClass = (article.status || 'unpublished').toLowerCase();
        const statusText = this.escapeHtml(article.status_text || '未发布');

        card.innerHTML = `
            <div class="article-header">
                <h3 class="article-title" title="${title}">${title}</h3>
                <div class="article-meta">
                    <span title="最后更新时间">${updatedAt}</span>
                    <span title="文章格式">${formatLabel}</span>
                    <span title="文件大小">${sizeLabel}</span>
                </div>
            </div>
            <div class="article-content">${excerpt}</div>
            <div class="article-footer">
                <span class="article-status ${statusClass}">${statusText}</span>
                <div class="article-actions">
                    <button class="btn btn-sm" onclick="app.editArticle('${article.id}')">编辑</button>
                    <button class="btn btn-sm btn-secondary" onclick="app.previewArticle('${article.id}')">预览</button>
                    <button class="btn btn-sm btn-danger" onclick="app.deleteArticle('${article.id}')">删除</button>
                </div>
            </div>
        `;

        return card;
    }

    formatDateTime(value) {
        if (!value) return '';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return '';
        }
        return date.toLocaleString();
    }

    formatFileSize(sizeKb) {
        const numericValue = Number(sizeKb);
        if (!Number.isFinite(numericValue) || numericValue < 0) {
            return '0 KB';
        }
        if (numericValue >= 1024) {
            return `${(numericValue / 1024).toFixed(1)} MB`;
        }
        return `${numericValue.toFixed(1)} KB`;
    }
      
    editArticle(articleId) {  
        // 编辑文章逻辑  
        console.log('编辑文章:', articleId);  
    }
    async deleteArticle(articleId) {  
        if (!confirm('确定要删除这篇文章吗？')) return;  
          
        try {  
            const response = await fetch(`/api/articles/${articleId}`, {  
                method: 'DELETE'  
            });  
              
            if (response.ok) {  
                this.showNotification('文章删除成功', 'success');  
                this.loadArticles(); // 重新加载文章列表  
            } else {  
                throw new Error('删除失败');  
            }
        } catch (error) {  
            console.error('删除文章失败:', error);  
            this.showNotification('删除文章失败', 'error');  
        }  
    }  
      
    previewArticle(articleId) {  
        // 预览文章逻辑  
        console.log('预览文章:', articleId);  
        // 这里可以打开预览窗口或跳转到预览页面  
    }  
      
    editArticle(articleId) {  
        // 编辑文章逻辑  
        console.log('编辑文章:', articleId);  
        // 这里可以跳转到编辑页面  
    }  
    
    // 添加新的预览方法  
    showPreview(content) {  
        if (window.previewPanelManager) {  
            window.previewPanelManager.show(content);  
        }  
    }  
    
    hidePreview() {  
        if (window.previewPanelManager) {  
            window.previewPanelManager.hide();  
        }  
    }

    showNotification(message, type = 'info') {  
        const notification = document.createElement('div');  
        notification.className = `notification ${type}`;  
        notification.innerHTML = `  
            <div class="notification-content">  
                <span>${message}</span>  
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>  
            </div>  
        `;  
          
        document.body.appendChild(notification);  
          
        // 3秒后自动移除  
        setTimeout(() => {  
            if (notification.parentElement) {  
                notification.remove();  
            }  
        }, 3000);  
    }  
}  
  
// 初始化应用  
let app;  
document.addEventListener('DOMContentLoaded', () => {  
    app = new AIWriteXApp();
    window.app = app;
});