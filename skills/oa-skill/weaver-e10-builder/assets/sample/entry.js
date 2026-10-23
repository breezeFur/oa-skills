import React, { useState, useEffect, Suspense } from 'react';
import { Route } from 'react-router-dom';
import { regOvProps, appInfo, regReactChildren } from '@weapp/utils';
import { getSimpleData } from './api/formApi.js';
import { asyncImport } from '@weapp/ecodesdk';

// 初始的空白模板项目
const { publicUrl } = appInfo('@weapp/ecodesdk');
const extract = (
  <Route path={`${publicUrl}/sp/custom/123123`}>
    <React.Suspense fallback={<div>Loading...</div>}>
    <>
      HELLO WORLD
    </>
    </React.Suspense>
  </Route>
);

regOvProps('weappEcodesdk', 'Switch', (props) => {
  regReactChildren(props, extract);
  return props;
}, 0);