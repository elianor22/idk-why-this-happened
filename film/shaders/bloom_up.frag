#version 430
uniform sampler2D uLow;   // lower (smaller) up-chain result
uniform sampler2D uCur;   // same-level down texture
uniform vec2 uLowTexel;
uniform float uW;
out vec4 o;
void main(){
    vec2 uv = (floor(gl_FragCoord.xy) + 0.5) * 0.5 * uLowTexel * 1.0;
    vec2 d = uLowTexel;
    vec3 s = textureLod(uLow, uv + vec2(-d.x, d.y), 0).rgb + 2.0*textureLod(uLow, uv + vec2(0, d.y), 0).rgb + textureLod(uLow, uv + vec2(d.x, d.y), 0).rgb
           + 2.0*textureLod(uLow, uv + vec2(-d.x, 0), 0).rgb + 4.0*textureLod(uLow, uv, 0).rgb + 2.0*textureLod(uLow, uv + vec2(d.x, 0), 0).rgb
           + textureLod(uLow, uv + vec2(-d.x,-d.y), 0).rgb + 2.0*textureLod(uLow, uv + vec2(0,-d.y), 0).rgb + textureLod(uLow, uv + vec2(d.x,-d.y), 0).rgb;
    s *= 1.0/16.0;
    vec2 cuv = (floor(gl_FragCoord.xy) + 0.5) / vec2(textureSize(uCur, 0));
    o = vec4(texture(uCur, cuv).rgb * uW + s, 1.0);
}
