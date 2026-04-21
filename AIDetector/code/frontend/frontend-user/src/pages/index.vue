<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h5">
            欢迎使用学术诚信检测系统
          </v-card-title>
          <v-card-text>
            <p>这里是系统的主页，您可以：</p>
            <v-list>
              <v-list-item>
                <v-list-item-title>
                  <v-icon start>mdi-file-upload</v-icon>
                  上传文件进行查重
                </v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>
                  <v-icon start>mdi-history</v-icon>
                  查看历史检测记录
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
//
</script>
