/**
 * 自定义环境补丁汇总入口（手动/遗留辅助）
 * 
  * vm-browser-gap-diagnose.js 不会自动扫描 ai-generated/ 目录；常规补丁应通过
 * --env ai-generated/<name>.js 显式加载。本文件只用于你手动注入
 * window.__aiFileContents__ 后集中执行多段补丁的场景。
 * 
 * @auto-generated 此文件由系统自动维护
 */

(function() {
    'use strict';
    
    console.log('[CustomEnv] Initializing custom environment patch loader...');
    
    // 自定义环境文件列表
    // 格式: { filename: '文件名', property: '补充的属性', source: '来源', enabled: true/false }
    const generatedFiles = [];
    
    // ==================== AI 文件内容存储 ====================
    // 在 isolated-vm 或手写 run.js 环境中，可以在加载本文件前注入所有文件内容
    // 当前 skill 不提供外部加载器；该对象由调用方手动填充
    const aiFileContents = window.__aiFileContents__ || {};
    
    // ==================== 加载统计 ====================
    const loadStats = {
        total: 0,
        success: 0,
        failed: 0,
        disabled: 0,
        errors: []
    };
    
    // ==================== 执行自定义补丁代码 ====================
    function executeAICode(filename, code) {
        try {
            // 创建独立的作用域执行代码
            const wrappedCode = `
                (function() {
                    try {
                        ${code}
                        return { success: true };
                    } catch (error) {
                        return { success: false, error: error.message, stack: error.stack };
                    }
                })();
            `;
            
            const result = eval(wrappedCode);
            
            if (result.success) {
                console.log(`[AI-Env] ✓ Loaded: ${filename}`);
                return { success: true };
            } else {
                console.error(`[AI-Env] ✗ Error in ${filename}:`, result.error);
                return { success: false, error: result.error };
            }
        } catch (error) {
            console.error(`[AI-Env] ✗ Failed to execute ${filename}:`, error.message);
            return { success: false, error: error.message };
        }
    }
    
    // ==================== 加载所有 AI 文件 ====================
    function loadAllAIFiles() {
        console.log(`[AI-Env] Loading ${generatedFiles.length} AI-generated files...`);
        
        loadStats.total = generatedFiles.length;
        
        generatedFiles.forEach(fileInfo => {
            // 检查是否启用
            if (fileInfo.enabled === false) {
                console.log(`[AI-Env] ⊗ Skipped (disabled): ${fileInfo.filename}`);
                loadStats.disabled++;
                return;
            }
            
            // 检查文件内容是否存在
            const code = aiFileContents[fileInfo.filename];
            if (!code) {
                console.warn(`[AI-Env] ⚠ No content for: ${fileInfo.filename}`);
                loadStats.failed++;
                loadStats.errors.push({
                    filename: fileInfo.filename,
                    error: 'File content not found'
                });
                return;
            }
            
            // 执行代码
            const result = executeAICode(fileInfo.filename, code);
            
            if (result.success) {
                loadStats.success++;
            } else {
                loadStats.failed++;
                loadStats.errors.push({
                    filename: fileInfo.filename,
                    error: result.error
                });
            }
        });
        
        // 输出加载统计
        console.log(`[AI-Env] Loading complete: ${loadStats.success} success, ${loadStats.failed} failed, ${loadStats.disabled} disabled`);
        
        if (loadStats.errors.length > 0) {
            console.error('[AI-Env] Errors:', loadStats.errors);
        }
    }
    
    // ==================== 动态添加 AI 文件 ====================
    function addAIFile(fileInfo, code) {
        // 添加到文件列表
        const existing = generatedFiles.findIndex(f => f.filename === fileInfo.filename);
        if (existing >= 0) {
            generatedFiles[existing] = fileInfo;
        } else {
            generatedFiles.push(fileInfo);
        }
        
        // 存储文件内容
        aiFileContents[fileInfo.filename] = code;
        
        // 如果启用，立即执行
        if (fileInfo.enabled !== false) {
            const result = executeAICode(fileInfo.filename, code);
            return result;
        }
        
        return { success: true, skipped: true };
    }
    
    // ==================== 启用/禁用 AI 文件 ====================
    function toggleAIFile(filename, enabled) {
        const file = generatedFiles.find(f => f.filename === filename);
        if (file) {
            file.enabled = enabled;
            console.log(`[AI-Env] ${enabled ? 'Enabled' : 'Disabled'}: ${filename}`);
            return true;
        }
        return false;
    }
    
    // ==================== 获取加载统计 ====================
    function getLoadStats() {
        return {
            ...loadStats,
            files: generatedFiles.map(f => ({
                filename: f.filename,
                property: f.property,
                platform: f.platform,
                enabled: f.enabled !== false
            }))
        };
    }
    
    // ==================== 全局导出 ====================
    window.__aiGeneratedEnv__ = {
        files: generatedFiles,
        fileContents: aiFileContents,
        count: generatedFiles.length,
        loadStats: loadStats,
        
        // 查询方法
        getByProperty: function(prop) {
            return generatedFiles.filter(f => f.property === prop);
        },
        getByPlatform: function(platform) {
            return generatedFiles.filter(f => f.platform === platform);
        },
        getByFilename: function(filename) {
            return generatedFiles.find(f => f.filename === filename);
        },
        
        // 管理方法
        addFile: addAIFile,
        toggleFile: toggleAIFile,
        getStats: getLoadStats,
        
        // 重新加载所有文件
        reload: function() {
            loadStats.success = 0;
            loadStats.failed = 0;
            loadStats.disabled = 0;
            loadStats.errors = [];
            loadAllAIFiles();
        }
    };
    
    // ==================== 自动加载 ====================
    // 如果有文件内容，自动加载所有 AI 文件
    if (Object.keys(aiFileContents).length > 0) {
        loadAllAIFiles();
    } else {
        console.log('[AI-Env] No AI file contents found. Waiting for injection...');
    }
    
    console.log('[AI-Env] Loader initialized. Use window.__aiGeneratedEnv__ to manage AI files.');
})();
