<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title class="text-h5">
            欢迎使用学术图像检测系统管理平台
          </v-card-title>
          <v-card-text>
            <p>这里是管理端的主页，您可以：</p>
            <v-list>
              <v-list-item> 
                <v-list-item-title>
                  <v-icon start>mdi-chart-bar</v-icon>
                  进行统计分析
                </v-list-item-title>
              </v-list-item>
              <v-list-item> 
                <v-list-item-title>
                  <v-icon start>mdi-folder</v-icon>
                  分类管理图像
                </v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>
                  <v-icon start>mdi-account-group</v-icon>
                  管理用户信息
                </v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>
                  <v-icon start>mdi-history</v-icon>
                  查看日志记录
                </v-list-item-title>
              </v-list-item>
              <v-list-item>
                <v-list-item-title> 
                  <v-icon start>mdi-gavel</v-icon>
                  审批人工审核
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
