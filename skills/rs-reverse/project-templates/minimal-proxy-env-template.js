/* 代理脚本 */
function get_envs(proxy_array) {
    for (let i = 0; i < proxy_array.length; i++) {
        handler = `{
            get: function(target, property, receiver) {
                   console.log('方法：get','    对象：${proxy_array[i]}','    属性：',property,'    属性类型：',typeof property,'    属性值类型：',typeof target[property]);
                   return target[property];
            },
            set: function(target, property, value, receiver){
                    console.log('方法：set','    对象：${proxy_array[i]}','    属性：',property,'    属性类型：',typeof property,'    属性值类型：',typeof target[property]);
                    return Reflect.set(...arguments);
            },
            apply: function(target, thisArg, argumentsList) {
                    console.log('方法：apply','    对象：${proxy_array[i]}','    参数：',argumentsList);
                    return Reflect.apply(target, thisArg, argumentsList);
            }
        }`;
        eval(`
            try {
                ${proxy_array[i]};
                ${proxy_array[i]} = new Proxy(${proxy_array[i]}, ${handler});
            } catch (e) {
                ${proxy_array[i]} = {};
                ${proxy_array[i]} = new Proxy(${proxy_array[i]}, ${handler});
            }
        `);
    }
}


/* 环境补充 */


/* 代理检测: 根据真实环境扩充检测对象 */
get_envs([
    'navigator',
    'location',
    'window',
    'document',
    'document.createElement',
    'document.appendChild',
    'document.removeChild',
    'div',
    'script',
    'script.parentElement',
    'meta',
    'document.getElementById'
])
